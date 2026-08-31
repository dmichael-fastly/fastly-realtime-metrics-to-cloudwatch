import asyncio
import aiohttp
import boto3
import json
import os
import time
import logging
import configparser
from typing import List, Dict, Any

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

def load_metrics_config() -> Dict[str, Any]:
    """Load and parse the metrics.ini configuration file."""
    global _metrics_config
    if _metrics_config is not None:
        return _metrics_config
        
    config = configparser.ConfigParser()
    # When deployed, metrics.ini is at the root of the lambda deployment package
    config_path = os.path.join(os.path.dirname(__file__), 'metrics.ini')
    
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        logger.warning(f"{config_path} not found, using default configuration.")
        config.read_dict({
            'edge': {'enabled': 'true', 'metrics': 'requests, hits, misses, errors, bandwidth, status_2xx, status_3xx, status_4xx, status_5xx'},
            'origin': {'enabled': 'false', 'metrics': 'responses'}
        })
        
    edge_enabled = config.getboolean('edge', 'enabled', fallback=True)
    
    origin_enabled = config.getboolean('origin', 'enabled', fallback=False)
    edge_metrics = []
    if edge_enabled:
        edge_metrics.extend([m.strip() for m in config.get('edge', 'metrics', fallback='').split(',') if m.strip()])
        edge_metrics.extend([m.strip() for m in config.get('edge', 'metrics_extra', fallback='').split(',') if m.strip()])
        
    
    origin_metrics = []
    if origin_enabled:
        origin_metrics.extend([m.strip() for m in config.get('origin', 'metrics', fallback='').split(',') if m.strip()])
        origin_metrics.extend([m.strip() for m in config.get('origin', 'metrics_extra', fallback='').split(',') if m.strip()])

    _metrics_config = {
        "edge": {"enabled": edge_enabled, "metrics": edge_metrics},
        "origin": {"enabled": origin_enabled, "metrics": origin_metrics}
    }
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

def parse_and_push_metrics(service_data: List[Dict[str, Any]], enable_hrm: bool = False) -> None:
    """Parse Fastly metrics and push them to AWS CloudWatch."""
    global _last_seen_timestamps
    metrics_config = load_metrics_config()
    metric_data = []
    
    for item in service_data:
        if "error" in item:
            continue
            
        service_id = item["service_id"]
        source = item["source"]
        data = item.get("data", {})
        
        ts_data = data.get("Data", [])
        if not ts_data:
            continue
            
        cache_key = f"{service_id}_{source}"
        last_seen = _last_seen_timestamps.get(cache_key, 0)
        
        if last_seen == 0:
            # On cold start, process the last 60 seconds of data to cover any gaps from the previous execution
            cutoff = int(time.time()) - 60
            last_seen = max(cutoff, ts_data[0].get("recorded", 1) - 1)
            
        unseen_data = [d for d in ts_data if d.get("recorded", 0) > last_seen]
        if not unseen_data:
            continue
        
        metrics_to_track = metrics_config[source]["metrics"]
        namespace = "Fastly/RealTime" if source == "edge" else "Fastly/OriginInspector"
        
        def flatten_metrics(raw_agg: Dict[str, Any]) -> Dict[str, float]:
            if source == "edge":
                flat_edge = {}
                for k, v in raw_agg.items():
                    if isinstance(v, (int, float)):
                        flat_edge[k] = float(v)
                # Synthesize bandwidth
                if "bandwidth" in metrics_to_track:
                    flat_edge["bandwidth"] = flat_edge.get("resp_body_bytes", 0.0) + flat_edge.get("resp_header_bytes", 0.0)
                if "misses" in metrics_to_track:
                    flat_edge["misses"] = flat_edge.get("miss", 0.0)
                return flat_edge
            
            flat = {}
            for origin_host, metrics in raw_agg.items():
                if isinstance(metrics, dict):
                    for k, v in metrics.items():
                        if isinstance(v, (int, float)):
                            flat[k] = flat.get(k, 0.0) + float(v)
            
            # Synthesize bandwidth for origin
            if "bandwidth" in metrics_to_track:
                flat["bandwidth"] = flat.get("resp_body_bytes", 0.0) + flat.get("resp_header_bytes", 0.0)
            return flat

        if enable_hrm:
            for d in unseen_data:
                recorded_ts = d.get("recorded", int(time.time()))
                aggregated = flatten_metrics(d.get("aggregated", {}))
                for metric_name in metrics_to_track:
                    metric_data.append({
                            '_namespace': namespace,
                            'MetricName': metric_name.capitalize(),
                            'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
                            'Timestamp': recorded_ts,
                            'Value': aggregated.get(metric_name, 0.0),
                            'Unit': 'Count' if 'bytes' not in metric_name and metric_name != 'bandwidth' else 'Bytes',
                            'StorageResolution': 1
                        })
        else:
            summed_metrics = {m: 0.0 for m in metrics_to_track}
            for d in unseen_data:
                aggregated = flatten_metrics(d.get("aggregated", {}))
                for metric_name in metrics_to_track:
                    if metric_name in aggregated:
                        summed_metrics[metric_name] += aggregated[metric_name]
            
            recorded_ts = unseen_data[-1].get("recorded", int(time.time()))
            
            for metric_name, value in summed_metrics.items():
                metric_data.append({
                        '_namespace': namespace,
                        'MetricName': metric_name.capitalize(),
                        'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
                        'Timestamp': recorded_ts,
                        'Value': value,
                        'Unit': 'Count' if 'bytes' not in metric_name and metric_name != 'bandwidth' else 'Bytes',
                        'StorageResolution': 60
                    })
        
        _last_seen_timestamps[cache_key] = unseen_data[-1].get("recorded", last_seen)

    if not metric_data:
        return

    # Group by namespace since boto3 requires it per PutMetricData call
    grouped_metrics = {}
    for item in metric_data:
        ns = item.pop('_namespace')
        if ns not in grouped_metrics:
            grouped_metrics[ns] = []
        grouped_metrics[ns].append(item)

    chunk_size = 1000
    for ns, items in grouped_metrics.items():
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            try:
                cloudwatch_client.put_metric_data(Namespace=ns, MetricData=chunk)
                logger.info(f"Successfully pushed {len(chunk)} metrics to CloudWatch ({ns}).")
            except Exception as e:
                logger.error(f"Failed to push metrics to CloudWatch ({ns}): {e}")

async def polling_loop(service_ids: List[str], api_token: str, poll_interval: int, enable_hrm: bool, duration_limit: int = 58) -> None:
    start_time = time.time()
    metrics_config = load_metrics_config()
    
    async with aiohttp.ClientSession() as session:
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
