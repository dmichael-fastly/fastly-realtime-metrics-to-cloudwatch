import re

filename = 'terraform/dashboard.tf'
with open(filename, 'r') as f:
    content = f.read()

def search_replacer(match):
    ns = match.group(1)
    metric = match.group(2)
    inner = match.group(3)
    return f'{{ expression = "SEARCH(\'{{{ns},FastlyServiceId}} FastlyServiceId=\\"$${{ServiceId}}\\" MetricName=\\"{metric}\\"\', \'Sum\', 60)", {inner} }}'

# I forgot to apply the EXACT SAME regex replacement to `dashboard.tf` in the previous step where I only updated `origin_dashboard.tf` correctly. Wait, I ran the python script on both files.
# Let me look at dashboard.tf. 
