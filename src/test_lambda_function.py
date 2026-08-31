import pytest
import asyncio
import time
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

def test_parse_and_push_metrics_standard_resolution(mock_cloudwatch):
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
            "Data": [{"recorded": 1000, "aggregated": {"requests": 10, "hits": 10}}]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data_1, enable_hrm=False)
    
    # Run 2: Next polling loop catches the next 3 buckets
    mock_data_2 = [{
        "service_id": "service_a",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": 1000, "aggregated": {"requests": 10, "hits": 10}}, # Already seen
                {"recorded": 1001, "aggregated": {"requests": 10, "hits": 10}},
                {"recorded": 1002, "aggregated": {"requests": 10, "hits": 8, "status_5xx": 2}},
                {"recorded": 1003, "aggregated": {"requests": 10, "hits": 10}}
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
    
    err_metric = next(m for m in metrics if m['MetricName'] == 'Status_5xx')
    assert err_metric['Value'] == 2.0 # 0 + 2 + 0

def test_parse_and_push_metrics_sparse_data(mock_cloudwatch):
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": True, "metrics": ["requests", "status_500"]},
        "origin": {"enabled": False, "metrics": []}
    }
    
    mock_data_1 = [{
        "service_id": "service_b",
        "source": "edge",
        "data": {"Data": [{"recorded": 1000, "aggregated": {"requests": 10}}]}
    }]
    lambda_function.parse_and_push_metrics(mock_data_1, enable_hrm=False)
    
    # status_500 is completely missing from all buckets (sparse data model)
    mock_data_2 = [{
        "service_id": "service_b",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": 1000, "aggregated": {"requests": 10}},
                {"recorded": 1001, "aggregated": {"requests": 10}}
            ]
        }
    }]
    lambda_function.parse_and_push_metrics(mock_data_2, enable_hrm=False)
    
    metrics = mock_cloudwatch.put_metric_data.call_args_list[-1][1]['MetricData']
    metric_names = [m['MetricName'] for m in metrics]
    
    # We expect Requests to be pushed, but NOT Status_500
    assert 'Requests' in metric_names
    assert 'Status_500' not in metric_names

def test_parse_and_push_metrics_high_resolution(mock_cloudwatch):
    lambda_function._last_seen_timestamps = {}
    lambda_function._metrics_config = {
        "edge": {"enabled": True, "metrics": ["requests"]},
        "origin": {"enabled": False, "metrics": []}
    }
    
    mock_data_1 = [{
        "service_id": "service_c",
        "source": "edge",
        "data": {"Data": [{"recorded": 1000, "aggregated": {"requests": 10}}]}
    }]
    lambda_function.parse_and_push_metrics(mock_data_1, enable_hrm=True)
    
    mock_data_2 = [{
        "service_id": "service_c",
        "source": "edge",
        "data": {
            "Data": [
                {"recorded": 1000, "aggregated": {"requests": 10}},
                {"recorded": 1001, "aggregated": {"requests": 5}},
                {"recorded": 1002, "aggregated": {"requests": 10}}
            ]
        }
    }]
    
    # Enable HRM
    lambda_function.parse_and_push_metrics(mock_data_2, enable_hrm=True)
    
    metrics = mock_cloudwatch.put_metric_data.call_args_list[-1][1]['MetricData']
    
    # HRM should push individual seconds, NOT aggregate them
    assert len(metrics) == 2
    assert metrics[0]['Value'] == 5.0
    assert metrics[0]['Timestamp'] == 1001
    assert metrics[0]['StorageResolution'] == 1
    
    assert metrics[1]['Value'] == 10.0
    assert metrics[1]['Timestamp'] == 1002
    assert metrics[1]['StorageResolution'] == 1

def test_lambda_handler_missing_env():
    with patch.dict('os.environ', {}, clear=True):
        response = lambda_function.lambda_handler({}, {})
        assert response["statusCode"] == 500

def test_parse_and_push_origin_flattening(mock_cloudwatch):
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
                "recorded": 1000, 
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
    
    waf_metric = next(m for m in metrics if m['MetricName'] == 'Waf_responses')
    assert waf_metric['Value'] == 2.0
