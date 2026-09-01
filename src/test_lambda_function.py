import asyncio
import configparser
import time

import pytest
from unittest.mock import MagicMock, patch

from src import lambda_function

@pytest.fixture
def mock_aiohttp_session():
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = MagicMock()
        mock_response.json.return_value = asyncio.Future()
        mock_response.json.return_value.set_result({"Data": []})
        mock_response.raise_for_status.return_value = None

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__.return_value = mock_response
        mock_get_ctx.__aexit__.return_value = asyncio.Future()
        mock_get_ctx.__aexit__.return_value.set_result(None)

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_get_ctx
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        yield mock_session_instance

@pytest.fixture
def mock_cloudwatch():
    with patch('src.lambda_function.cloudwatch_client') as mock_cw:
        yield mock_cw

@pytest.mark.asyncio
async def test_fetch_fastly_metrics_success(mock_aiohttp_session):
    result = await lambda_function.fetch_fastly_metrics(mock_aiohttp_session, "service123", "fake_token", "edge")

    assert result["service_id"] == "service123"
    assert result["source"] == "edge"
    assert "data" in result

@pytest.mark.parametrize("fastly_name,cloudwatch_name", [
    ("requests", "Requests"),
    ("status_5xx", "Status5xx"),
    ("status_500", "Status500"),
    ("waf_responses", "WafResponses"),
    ("edge_hit_requests", "EdgeHitRequests"),
    ("latency_0_to_1ms", "Latency0To1ms"),
    ("latency_10000_to_60000ms", "Latency10000To60000ms"),
    ("latency_60000ms", "Latency60000ms"),
    ("compute_request_time_ms", "ComputeRequestTimeMs"),
    ("ddos_protection_requests_detect_count", "DdosProtectionRequestsDetectCount"),
])
def test_to_cloudwatch_name(fastly_name, cloudwatch_name):
    assert lambda_function.to_cloudwatch_name(fastly_name) == cloudwatch_name

@pytest.mark.parametrize("metric_name,unit", [
    ("requests", "Count"),
    ("bandwidth", "Bytes"),
    ("resp_body_bytes", "Bytes"),
    ("edge_resp_header_bytes", "Bytes"),
    ("miss_time", "Seconds"),
    ("pass_time", "Seconds"),
    ("compute_request_time_ms", "Milliseconds"),
    ("latency_0_to_1ms", "Count"),  # latency buckets are response counts, not durations
])
def test_get_metric_unit(metric_name, unit):
    assert lambda_function.get_metric_unit(metric_name) == unit

def test_parse_metrics_list_reads_all_extra_sections():
    config = configparser.ConfigParser()
    config.read_dict({
        "edge": {
            "enabled": "true",
            "metrics": "requests, hits, status_500",
            "metrics_extra_status": "status_200, status_500",
            "metrics_extra_volume": "edge_requests, , requests",
        },
        "origin": {"enabled": "true", "metrics": "responses"},
    })

    edge = lambda_function.parse_metrics_list(config, "edge")

    # Every metrics* key is read, duplicates collapse, order is preserved, blanks dropped
    assert edge == ["requests", "hits", "status_500", "status_200", "edge_requests"]
    assert lambda_function.parse_metrics_list(config, "origin") == ["responses"]

def test_parse_metrics_list_missing_section():
    config = configparser.ConfigParser()
    assert lambda_function.parse_metrics_list(config, "edge") == []

def test_load_metrics_config_reads_extra_sections_from_ini(tmp_path, monkeypatch):
    ini = tmp_path / "metrics.ini"
    ini.write_text(
        "[edge]\n"
        "enabled = true\n"
        "metrics = requests, hits\n"
        "metrics_extra_status = status_200\n"
        "metrics_extra_shield = shield_fetches\n"
        "\n"
        "[origin]\n"
        "enabled = false\n"
        "metrics = responses\n"
    )
    # load_metrics_config resolves metrics.ini relative to the module file
    monkeypatch.setattr(lambda_function, "__file__", str(tmp_path / "lambda_function.py"))
    monkeypatch.setattr(lambda_function, "_metrics_config", None)

    config = lambda_function.load_metrics_config()

    assert config["edge"]["metrics"] == ["requests", "hits", "status_200", "shield_fetches"]
    assert config["origin"] == {"enabled": False, "metrics": []}

def test_terraform_references_only_published_metric_names():
    """Every CloudWatch metric name referenced in the dashboards and alarms must be
    derivable from a metric id in metrics.ini via to_cloudwatch_name — this is what
    keeps the charts from silently rendering empty."""
    import re
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent

    # Collect every metric id mentioned in metrics.ini, including commented-out
    # example lines (widgets for those are gated off in Terraform, but the names
    # still appear in the .tf source)
    ini_ids = set()
    for line in (repo_root / "metrics.ini").read_text().splitlines():
        match = re.match(r"^\s*[#;]?\s*metrics\w*\s*=\s*(.+)$", line)
        if match:
            ini_ids.update(m.strip() for m in match.group(1).split(",") if m.strip())
    published = {lambda_function.to_cloudwatch_name(m) for m in ini_ids}

    referenced = {}
    for tf_name in ["dashboard.tf", "origin_dashboard.tf", "alarms.tf"]:
        content = (repo_root / "terraform" / tf_name).read_text()
        names = re.findall(r'\["Fastly/(?:RealTime|OriginInspector)",\s*"([^"]+)"', content)
        names += re.findall(r'namespace\s*=\s*"Fastly/(?:RealTime|OriginInspector)"[\s\S]{0,200}?metric_name\s*=\s*"([^"]+)"', content)
        names += re.findall(r'metric_name\s*=\s*"([^"]+)"[\s\S]{0,200}?namespace\s*=\s*"Fastly/(?:RealTime|OriginInspector)"', content)
        for name in names:
            referenced.setdefault(name, []).append(tf_name)

    assert referenced, "expected to find metric references in the Terraform files"
    unknown = {name: files for name, files in referenced.items() if name not in published}
    assert not unknown, f"Terraform references metric names the Lambda never publishes: {unknown}"

def test_parse_and_push_metrics_standard_resolution(mock_cloudwatch):
    now = int(time.time())
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": True, "metrics": ["requests", "hits", "status_5xx"]},
        "origin": {"enabled": False, "metrics": []}
    }

    # Run 1: Cold start sets the last_seen timestamp
    mock_data_1 = [{
        "service_id": "service_a",
        "source": "edge",
        "data": {
            "Data": [{"recorded": now - 10, "aggregated": {"requests": 10, "hits": 10}}]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data_1, enable_hrm=False)

    # Run 2: Next polling loop catches the next 3 buckets
    mock_data_2 = [{
        "service_id": "service_a",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": now - 10, "aggregated": {"requests": 10, "hits": 10}}, # Already seen
                {"recorded": now - 9, "aggregated": {"requests": 10, "hits": 10}},
                {"recorded": now - 8, "aggregated": {"requests": 10, "hits": 8, "status_5xx": 2}},
                {"recorded": now - 7, "aggregated": {"requests": 10, "hits": 10}}
            ]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data_2, enable_hrm=False)

    # Standard resolution sums the 3 unseen buckets together
    calls = mock_cloudwatch.put_metric_data.call_args_list
    metrics = calls[-1][1]['MetricData']

    req_metric = next(m for m in metrics if m['MetricName'] == 'Requests')
    assert req_metric['Value'] == 30.0 # 10 + 10 + 10
    assert req_metric['StorageResolution'] == 60

    err_metric = next(m for m in metrics if m['MetricName'] == 'Status5xx')
    assert err_metric['Value'] == 2.0 # 0 + 2 + 0

def test_parse_and_push_metrics_sparse_data(mock_cloudwatch):
    now = int(time.time())
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": True, "metrics": ["requests", "status_500"]},
        "origin": {"enabled": False, "metrics": []}
    }

    mock_data_1 = [{
        "service_id": "service_b",
        "source": "edge",
        "data": {"Data": [{"recorded": now - 10, "aggregated": {"requests": 10}}]}
    }]
    lambda_function.parse_and_push_metrics(mock_data_1, enable_hrm=False)

    # status_500 is completely missing from all buckets (sparse data model)
    mock_data_2 = [{
        "service_id": "service_b",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": now - 10, "aggregated": {"requests": 10}},
                {"recorded": now - 9, "aggregated": {"requests": 10}}
            ]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data_2, enable_hrm=False)

    metrics = mock_cloudwatch.put_metric_data.call_args_list[-1][1]['MetricData']

    # A missing key means zero traffic, so tracked metrics are zero-filled (keeps
    # charts gap-free and lets threshold alarms evaluate)
    req_metric = next(m for m in metrics if m['MetricName'] == 'Requests')
    assert req_metric['Value'] == 10.0
    err_metric = next(m for m in metrics if m['MetricName'] == 'Status500')
    assert err_metric['Value'] == 0.0

def test_parse_and_push_metrics_cold_start_skips_stale_buckets(mock_cloudwatch):
    now = int(time.time())
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": True, "metrics": ["requests"]},
        "origin": {"enabled": False, "metrics": []}
    }

    # The realtime API returns up to 120s of history; on cold start only the
    # last 15 seconds should be processed to avoid double-counting old data
    mock_data = [{
        "service_id": "service_stale",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": now - 60, "aggregated": {"requests": 100}},
                {"recorded": now - 5, "aggregated": {"requests": 7}}
            ]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data, enable_hrm=False)

    metrics = mock_cloudwatch.put_metric_data.call_args_list[-1][1]['MetricData']
    req_metric = next(m for m in metrics if m['MetricName'] == 'Requests')
    assert req_metric['Value'] == 7.0

def test_parse_and_push_metrics_high_resolution(mock_cloudwatch):
    now = int(time.time())
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": True, "metrics": ["requests"]},
        "origin": {"enabled": False, "metrics": []}
    }

    mock_data_1 = [{
        "service_id": "service_c",
        "source": "edge",
        "data": {"Data": [{"recorded": now - 10, "aggregated": {"requests": 10}}]}
    }]
    lambda_function.parse_and_push_metrics(mock_data_1, enable_hrm=True)

    mock_data_2 = [{
        "service_id": "service_c",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": now - 10, "aggregated": {"requests": 10}},
                {"recorded": now - 9, "aggregated": {"requests": 5}},
                {"recorded": now - 8, "aggregated": {"requests": 10}}
            ]
        }
    }]

    # Enable HRM
    lambda_function.parse_and_push_metrics(mock_data_2, enable_hrm=True)

    metrics = mock_cloudwatch.put_metric_data.call_args_list[-1][1]['MetricData']

    # HRM should push individual seconds, NOT aggregate them
    assert len(metrics) == 2
    assert metrics[0]['Value'] == 5.0
    assert metrics[0]['Timestamp'] == now - 9
    assert metrics[0]['StorageResolution'] == 1

    assert metrics[1]['Value'] == 10.0
    assert metrics[1]['Timestamp'] == now - 8
    assert metrics[1]['StorageResolution'] == 1

def test_lambda_handler_missing_env():
    with patch.dict('os.environ', {}, clear=True):
        response = lambda_function.lambda_handler({}, {})
        assert response["statusCode"] == 500

def test_parse_and_push_origin_flattening(mock_cloudwatch):
    now = int(time.time())
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": False, "metrics": []},
        "origin": {"enabled": True, "metrics": ["responses", "waf_responses"]}
    }

    mock_data = [{
        "service_id": "service_origin",
        "source": "origin",
        "data": {
            "Data": [{
                "recorded": now - 5,
                "aggregated": {
                    "origin1": {"responses": 10, "waf_responses": 2},
                    "origin2": {"responses": 20}
                }
            }]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data, enable_hrm=False)

    metrics = mock_cloudwatch.put_metric_data.call_args_list[-1][1]['MetricData']

    req_metric = next(m for m in metrics if m['MetricName'] == 'Responses')
    assert req_metric['Value'] == 30.0 # 10 + 20
    assert req_metric['StorageResolution'] == 60

    waf_metric = next(m for m in metrics if m['MetricName'] == 'WafResponses')
    assert waf_metric['Value'] == 2.0
