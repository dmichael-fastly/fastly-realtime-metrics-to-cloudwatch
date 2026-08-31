import boto3

cw = boto3.client('cloudwatch')
try:
    resp = cw.get_dashboard(DashboardName="Fastly-Origin-Metrics")
    import json
    dash = json.loads(resp['DashboardBody'])
    print(json.dumps(dash['variables'], indent=2))
except Exception as e:
    print(e)
