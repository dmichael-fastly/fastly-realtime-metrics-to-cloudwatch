with open('terraform/origin_dashboard.tf', 'r') as f:
    c = f.read()

# Fix Bandwidth Output
c = c.replace('["Fastly/OriginInspector", "Resp_body_bytes"', '["Fastly/OriginInspector", "Bandwidth"')
c = c.replace('id = "obytes", label = "Body Bytes', 'id = "obw", label = "Bandwidth')
c = c.replace('["Fastly/OriginInspector", "Resp_header_bytes", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "ohbytes", label = "Header Bytes ($${PROP(\\"FastlyServiceId\\")})" }]', '')

# Fix view for latency histogram
c = c.replace('view    = "bar"', 'view    = "timeSeries"')

with open('terraform/origin_dashboard.tf', 'w') as f:
    f.write(c)

