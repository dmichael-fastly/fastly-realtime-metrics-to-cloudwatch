import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs')

# Get logs from the last 2 minutes
start_time = int((datetime.now() - timedelta(minutes=2)).timestamp() * 1000)

paginator = logs.get_paginator('filter_log_events')
pages = paginator.paginate(
    logGroupName='/aws/lambda/fastly-realtime-metrics-poller',
    startTime=start_time
)

count = 0
for page in pages:
    for event in page['events']:
        if 'Successfully pushed' in event['message']:
            print(f"[{event['timestamp']}] {event['message']}")
            count += 1
            if count >= 4:
                break
    if count >= 4:
        break
