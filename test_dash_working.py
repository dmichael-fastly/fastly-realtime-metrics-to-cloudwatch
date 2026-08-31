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
            "property": "Dim.FastlyServiceId"
        }
    ],
    "widgets": []
}

try:
    cw.put_dashboard(
        DashboardName="Test-Dashboard-Working-Pattern",
        DashboardBody=json.dumps(dashboard_body)
    )
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
