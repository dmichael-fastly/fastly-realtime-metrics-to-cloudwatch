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
            "populateFrom": "metrics",
            "search": "{Fastly/RealTime,FastlyServiceId}",
            "property": "FastlyServiceId"
        }
    ],
    "widgets": []
}

try:
    cw.put_dashboard(
        DashboardName="Test-Dashboard-Variables-3",
        DashboardBody=json.dumps(dashboard_body)
    )
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
