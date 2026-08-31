import urllib.request
import json
import re

url = "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/DashboardVariables_JSON.html"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    html = response.read().decode('utf-8')
    
    # Try to extract JSON examples
    matches = re.findall(r'<code[^>]*>(.*?)</code>', html, re.DOTALL)
    for m in matches:
        if 'variables' in m.lower():
            print(m.strip())
            print("-" * 50)
