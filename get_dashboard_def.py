import boto3

cw = boto3.client('cloudwatch')
try:
    resp = cw.get_dashboard(DashboardName="Fastly-RealTime-Metrics")
    print(resp['DashboardBody'][:1000])
except Exception as e:
    print(e)
