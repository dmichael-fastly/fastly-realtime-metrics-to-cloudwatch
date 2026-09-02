import asyncio
import aiohttp
import boto3
import os
import time
import logging
from typing import Any, Dict, List, Optional

try:
    from src.metrics_config import to_cloudwatch_name, get_metric_unit, parse_metrics_list, load as load_config_file
except ImportError:
    # In the Lambda deployment package all modules sit at the zip root
    from metrics_config import to_cloudwatch_name, get_metric_unit, parse_metrics_list, load as load_config_file

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global clients for reuse across lambda invocations
from botocore.config import Config

boto_config = Config(retries={'max_attempts': 5, 'mode': 'standard'})
secrets_client = boto3.client('secretsmanager', config=boto_config)
cloudwatch_client = boto3.client('cloudwatch', config=boto_config)

# Initialize global caches
_fastly_api_token = None
_last_seen_timestamps = {}
_metrics_config = None

# On cold start, only process this many seconds of history to cover the gap
# since the previous lambda exited (which runs for 58s every 60s)
COLD_START_WINDOW_SECONDS = 15

def load_metrics_config() -> Dict[str, Any]:
    """Load and parse the metrics.ini configuration file (cached across invocations)."""
    global _metrics_config
    if _metrics_config is not None:
        return _metrics_config

    # When deployed, metrics.ini is at the root of the lambda deployment package
    config_path = os.path.join(os.path.dirname(__file__), 'metrics.ini')
    if not os.path.exists(config_path):
        logger.warning(f"{config_path} not found, using default configuration.")

    _metrics_config = load_config_file(config_path)
    edge_count = len(_metrics_config['edge']['metrics'])
    origin_count = len(_metrics_config['origin']['metrics'])
    logger.info(f"Metrics config loaded: {edge_count} edge and {origin_count} origin metrics tracked (this drives CloudWatch custom metric costs).")
    return _metrics_config

def get_api_token(secret_arn: str) -> str:
    """Retrieve the Fastly API token from AWS Secrets Manager."""
    global _fastly_api_token
    if _fastly_api_token is None:
        try:
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            _fastly_api_token = response['SecretString']
        except Exception as e:
            logger.error(f"Failed to retrieve secret from Secrets Manager: {e}")
            raise
    return _fastly_api_token

async def fetch_fastly_metrics(session: aiohttp.ClientSession, service_id: str, api_token: str, source: str, max_retries: int = 3) -> Dict[str, Any]:
    """Fetch real-time metrics for a single Fastly service and source asynchronously."""
    if source == "edge":
        url = f"https://rt.fastly.com/v1/channel/{service_id}/ts/h"
    else:
        url = f"https://rt.fastly.com/v1/origins/{service_id}/ts/h"

    headers = {
        "Fastly-Key": api_token,
        "Accept": "application/json"
    }

    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return {"service_id": service_id, "source": source, "data": data}
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch {source} metrics for service {service_id} after {max_retries} attempts: {e}")
                return {"service_id": service_id, "source": source, "error": str(e)}

            backoff = 0.1 * (2 ** attempt)
            logger.warning(f"Transient error fetching {source} metrics for {service_id} (Attempt {attempt+1}/{max_retries}). Retrying in {backoff}s...")
            await asyncio.sleep(backoff)

def flatten_edge(raw_agg: Dict[str, Any], metrics_to_track: List[str]) -> Dict[str, float]:
    """Flatten one second of edge data; synthesizes `bandwidth` and `misses`."""
    flat = {k: float(v) for k, v in raw_agg.items() if isinstance(v, (int, float))}
    if "bandwidth" in metrics_to_track:
        flat["bandwidth"] = flat.get("resp_body_bytes", 0.0) + flat.get("resp_header_bytes", 0.0)
    if "misses" in metrics_to_track:
        flat["misses"] = flat.get("miss", 0.0)
    return flat

def flatten_origin(raw_agg: Dict[str, Any], metrics_to_track: List[str]) -> Dict[str, float]:
    """Sum one second of origin data across all origin hosts; synthesizes `bandwidth`."""
    flat = {}
    for origin_host, metrics in raw_agg.items():
        if isinstance(metrics, dict):
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    flat[k] = flat.get(k, 0.0) + float(v)
    if "bandwidth" in metrics_to_track:
        flat["bandwidth"] = flat.get("resp_body_bytes", 0.0) + flat.get("resp_header_bytes", 0.0)
    return flat

def select_unseen(ts_data: List[Dict[str, Any]], last_seen: int, now: int) -> List[Dict[str, Any]]:
    """Return the buckets newer than last_seen; on cold start (last_seen == 0),
    only look back COLD_START_WINDOW_SECONDS to avoid double-counting history."""
    if not ts_data:
        return []
    if last_seen == 0:
        cutoff = now - COLD_START_WINDOW_SECONDS
        last_seen = max(cutoff, ts_data[0].get("recorded", 1) - 1)
    return [d for d in ts_data if d.get("recorded", 0) > last_seen]

def build_datapoint(metric_name: str, value: float, service_id: str, timestamp: int, resolution: int) -> Dict[str, Any]:
    return {
        'MetricName': to_cloudwatch_name(metric_name),
        'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
        'Timestamp': timestamp,
        'Value': value,
        'Unit': get_metric_unit(metric_name),
        'StorageResolution': resolution
    }

def build_datapoints(unseen_data: List[Dict[str, Any]], source: str, service_id: str,
                     metrics_to_track: List[str], enable_hrm: bool, now: int) -> List[Dict[str, Any]]:
    """Build CloudWatch datapoints for one service/source. A metric id missing from a
    bucket means zero traffic (Fastly's sparse model), so tracked metrics are zero-filled."""
    flatten = flatten_edge if source == "edge" else flatten_origin
    datapoints = []

    if enable_hrm:
        for d in unseen_data:
            recorded_ts = d.get("recorded", now)
            aggregated = flatten(d.get("aggregated", {}), metrics_to_track)
            for metric_name in metrics_to_track:
                datapoints.append(build_datapoint(metric_name, aggregated.get(metric_name, 0.0), service_id, recorded_ts, 1))
    else:
        summed = {m: 0.0 for m in metrics_to_track}
        for d in unseen_data:
            aggregated = flatten(d.get("aggregated", {}), metrics_to_track)
            for metric_name in metrics_to_track:
                if metric_name in aggregated:
                    summed[metric_name] += aggregated[metric_name]
        recorded_ts = unseen_data[-1].get("recorded", now)
        for metric_name, value in summed.items():
            datapoints.append(build_datapoint(metric_name, value, service_id, recorded_ts, 60))

    return datapoints

def push_to_cloudwatch(metrics_by_namespace: Dict[str, List[Dict[str, Any]]], chunk_size: int = 1000) -> None:
    for ns, items in metrics_by_namespace.items():
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            try:
                cloudwatch_client.put_metric_data(Namespace=ns, MetricData=chunk)
                logger.info(f"Successfully pushed {len(chunk)} metrics to CloudWatch ({ns}).")
            except Exception as e:
                logger.error(f"Failed to push metrics to CloudWatch ({ns}): {e}")

def parse_and_push_metrics(service_data: List[Dict[str, Any]], enable_hrm: bool = False, now: Optional[int] = None) -> None:
    """Parse Fastly metrics and push them to AWS CloudWatch."""
    global _last_seen_timestamps
    now = int(time.time()) if now is None else now
    metrics_config = load_metrics_config()
    metrics_by_namespace = {}

    for item in service_data:
        if "error" in item:
            continue

        service_id = item["service_id"]
        source = item["source"]
        ts_data = item.get("data", {}).get("Data", [])
        if not ts_data:
            continue

        cache_key = f"{service_id}_{source}"
        unseen_data = select_unseen(ts_data, _last_seen_timestamps.get(cache_key, 0), now)
        if not unseen_data:
            continue

        namespace = "Fastly/RealTime" if source == "edge" else "Fastly/OriginInspector"
        datapoints = build_datapoints(unseen_data, source, service_id, metrics_config[source]["metrics"], enable_hrm, now)
        metrics_by_namespace.setdefault(namespace, []).extend(datapoints)

        _last_seen_timestamps[cache_key] = unseen_data[-1].get("recorded", _last_seen_timestamps.get(cache_key, 0))

    if metrics_by_namespace:
        push_to_cloudwatch(metrics_by_namespace)

async def polling_loop(service_ids: List[str], api_token: str, poll_interval: int, enable_hrm: bool, duration_limit: int = 58) -> None:
    start_time = time.time()
    metrics_config = load_metrics_config()

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            if elapsed >= duration_limit:
                logger.info("Approaching 60-second limit, exiting polling loop.")
                break

            tasks = []
            for sid in service_ids:
                if metrics_config["edge"]["enabled"]:
                    tasks.append(fetch_fastly_metrics(session, sid, api_token, "edge"))
                if metrics_config["origin"]["enabled"]:
                    tasks.append(fetch_fastly_metrics(session, sid, api_token, "origin"))

            if tasks:
                results = await asyncio.gather(*tasks)
                parse_and_push_metrics(results, enable_hrm)

            processing_time = time.time() - current_time
            sleep_time = max(0.1, poll_interval - processing_time)

            if (current_time + sleep_time - start_time) >= duration_limit:
                break

            await asyncio.sleep(sleep_time)

def lambda_handler(event, context):
    secret_arn = os.environ.get('SECRET_ARN')
    service_ids_str = os.environ.get('FASTLY_SERVICE_IDS', '')
    poll_interval_str = os.environ.get('POLL_INTERVAL_SECONDS', '10')
    enable_hrm = os.environ.get('ENABLE_HIGH_RESOLUTION_METRICS', 'false').lower() == 'true'

    if not secret_arn or not service_ids_str:
        logger.error("Missing required environment variables (SECRET_ARN, FASTLY_SERVICE_IDS)")
        return {"statusCode": 500, "body": "Configuration error"}

    try:
        poll_interval = int(poll_interval_str)
    except ValueError:
        logger.warning(f"Invalid POLL_INTERVAL_SECONDS '{poll_interval_str}', defaulting to 10.")
        poll_interval = 10

    service_ids = [sid.strip() for sid in service_ids_str.split(',') if sid.strip()]
    if not service_ids:
        logger.error("No valid Fastly Service IDs provided.")
        return {"statusCode": 500, "body": "Configuration error"}

    try:
        api_token = get_api_token(secret_arn)
    except Exception:
        return {"statusCode": 500, "body": "Failed to retrieve API token"}

    asyncio.run(polling_loop(service_ids, api_token, poll_interval, enable_hrm))

    return {
        "statusCode": 200,
        "body": "Successfully completed polling cycle."
    }
