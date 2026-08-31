import boto3
import json

cw = boto3.client('cloudwatch')

dashboard_body = {
    "variables": [
        {
            "id": "ServiceId",
            "type": "property",
            "inputType": "select",
            "visible": True,
            "value": "FastlyServiceId",
            "label": "Fastly Service",
            "populateFrom": "metrics",
            "search": "{Fastly/RealTime,FastlyServiceId} MetricName=\"Requests\"",
            "property": "FastlyServiceId"
        }
    ],
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 2,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [{"expression": "SEARCH('{Fastly/RealTime,FastlyServiceId} FastlyServiceId=\"${ServiceId}\" MetricName=\"Requests\"', 'Sum', 60)", "id": "reqs"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-east-1"
            }
        }
    ]
}

try:
    cw.put_dashboard(
        DashboardName="Test-Dashboard-Variables",
        DashboardBody=json.dumps(dashboard_body)
    )
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
