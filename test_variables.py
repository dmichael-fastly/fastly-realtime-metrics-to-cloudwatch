import boto3

cw = boto3.client('cloudwatch')
paginator = cw.get_paginator('list_metrics')
for response in paginator.paginate(Namespace='Fastly/RealTime'):
    print(response['Metrics'])
    break
