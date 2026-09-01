with open('terraform/dashboard.tf', 'r') as f:
    c = f.read()

# Fix error_rate math
c = c.replace('expression = "SUM(errs) / SUM(reqs) * 100"', 'expression = "(errs / reqs) * 100"')

# Fix Bandwidth Output
c = c.replace('["Fastly/RealTime", "Resp_body_bytes"', '["Fastly/RealTime", "Bandwidth"')
c = c.replace('id = "body", label = "Body Bytes', 'id = "bw", label = "Bandwidth')
c = c.replace('["Fastly/RealTime", "Resp_header_bytes", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "headers", label = "Header Bytes ($${PROP(\\"FastlyServiceId\\")})" }]', '')

with open('terraform/dashboard.tf', 'w') as f:
    f.write(c)

# Add missing metrics to metrics.ini
def update_metrics_ini(filename):
    with open(filename, 'r') as f:
        c = f.read()
    c = c.replace(
        'metrics = requests, hits, errors, bandwidth, status_2xx, status_3xx, status_4xx, status_5xx',
        'metrics = requests, hits, misses, errors, bandwidth, status_2xx, status_3xx, status_4xx, status_5xx, status_400, status_401, status_403, status_404, status_500, status_502, status_503, status_504, compute_request_time_ms, compute_execution_time_ms, miss_time, pass_time'
    )
    with open(filename, 'w') as f:
        f.write(c)

update_metrics_ini('metrics.ini')
update_metrics_ini('metrics.ini.example')

