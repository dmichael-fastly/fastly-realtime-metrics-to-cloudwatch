import boto3
import json

cw = boto3.client('cloudwatch')

dashboard_body = {
    "variables": [],
    "widgets": []
}

# I'm going to let Boto3 error if it fails, but I really want to just create a dummy dashboard, 
# then I can go to console, but I don't have console access. I'm an agent.
# Let me write a script that tries different variable configurations until one gives me the right results.
