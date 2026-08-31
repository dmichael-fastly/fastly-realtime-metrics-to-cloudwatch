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
            "label": "Fastly Service",
            "populateFrom": "FastlyServiceId",
            "search": "{Fastly/RealTime,FastlyServiceId} MetricName=\"Requests\"",
            "property": "FastlyServiceId"
        }
    ],
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "view": "timeSeries",
                "stacked": False,
                "metrics": [
                    [ "Fastly/RealTime", "Requests", "FastlyServiceId", "${ServiceId}", { "id": "reqs", "label": "Requests (${PROP(\"FastlyServiceId\")})" } ]
                ],
                "region": "us-east-1"
            }
        }
    ]
}

try:
    cw.put_dashboard(
        DashboardName="Test-Dashboard-Working-4",
        DashboardBody=json.dumps(dashboard_body)
    )
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
