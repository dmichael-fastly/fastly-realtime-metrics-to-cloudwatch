import os
import requests
import json
import time
import subprocess
import datetime
from datetime import timezone

SERVICE_ID = "cVnu9mYB3Cvmob3lsqjQU3"
api_key = ""
with open("terraform/terraform.tfvars", "r") as f:
    for line in f:
        if line.startswith("fastly_api_key"):
            api_key = line.split("=")[1].strip().strip('"')
            break

headers = {"Fastly-Key": api_key, "Accept": "application/json"}

now = int(time.time())
now_dt = datetime.datetime.fromtimestamp(now, tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
start_dt = now_dt - datetime.timedelta(hours=6)
start_ts = int(start_dt.timestamp())
end_ts = int(now_dt.timestamp())

start_iso = start_dt.isoformat().replace("+00:00", "Z")
end_iso = now_dt.isoformat().replace("+00:00", "Z")

# Fetch Edge Data
res = requests.get(f"https://api.fastly.com/stats/service/{SERVICE_ID}?from={start_ts}&to={end_ts}&by=hour", headers=headers)
fastly_edge = res.json().get("data", [])

# Map of Fastly fields to CW Metric Names (from our mapping logic)
edge_fields = {
    "requests": "Requests",
    "hits": "Hits",
    "miss": "Misses", # The fastly API returns 'miss' not 'misses'
    "errors": "Errors",
    "status_2xx": "Status2xx",
    "status_3xx": "Status3xx",
    "status_4xx": "Status4xx",
    "status_5xx": "Status5xx",
    "status_400": "Status400",
    "status_401": "Status401",
    "status_403": "Status403",
    "status_404": "Status404",
    "status_500": "Status500",
    "status_502": "Status502",
    "status_503": "Status503",
    "status_504": "Status504"
}

print(f"\n--- AUDITING EDGE METRICS (Last 6 Hours) ---")
for fastly_key, cw_name in edge_fields.items():
    total_fastly = sum(point.get(fastly_key, 0) for point in fastly_edge)
    
    cmd = f'aws cloudwatch get-metric-statistics --namespace Fastly/RealTime --metric-name {cw_name} --dimensions Name=FastlyServiceId,Value={SERVICE_ID} --start-time {start_iso} --end-time {end_iso} --period 3600 --statistics Sum'
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    cw_data = json.loads(out)
    total_cw = sum(dp['Sum'] for dp in cw_data['Datapoints'])
    
    diff = total_cw - total_fastly
    pct = (diff / total_fastly * 100) if total_fastly > 0 else 0
    print(f"{cw_name.ljust(15)} | Fastly: {total_fastly:<10} | CW: {total_cw:<10} | Diff: {diff:<6} ({pct:.2f}%)")

# Note: bandwidth requires special sum of resp_body_bytes + resp_header_bytes for Fastly edge, 
# while our CW metric is named 'Bandwidth'.
fastly_bw = sum(point.get("resp_body_bytes", 0) + point.get("resp_header_bytes", 0) for point in fastly_edge)
cmd = f'aws cloudwatch get-metric-statistics --namespace Fastly/RealTime --metric-name Bandwidth --dimensions Name=FastlyServiceId,Value={SERVICE_ID} --start-time {start_iso} --end-time {end_iso} --period 3600 --statistics Sum'
out = subprocess.check_output(cmd, shell=True).decode('utf-8')
total_cw_bw = sum(dp['Sum'] for dp in json.loads(out)['Datapoints'])
diff = total_cw_bw - fastly_bw
pct = (diff / fastly_bw * 100) if fastly_bw > 0 else 0
print(f"{'Bandwidth'.ljust(15)} | Fastly: {fastly_bw:<10} | CW: {total_cw_bw:<10} | Diff: {diff:<6} ({pct:.2f}%)")


# Note: miss_time and pass_time are averages in CW, need Average not Sum
for cw_name in ["MissTime", "PassTime"]:
    fastly_key = cw_name.lower()
    cmd = f'aws cloudwatch get-metric-statistics --namespace Fastly/RealTime --metric-name {cw_name} --dimensions Name=FastlyServiceId,Value={SERVICE_ID} --start-time {start_iso} --end-time {end_iso} --period 3600 --statistics Average'
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    dps = json.loads(out)['Datapoints']
    total_cw_avg = sum(dp['Average'] for dp in dps) / len(dps) if dps else 0
    
    # Fastly historic stats API doesn't always provide good historic averages for times in the same way, 
    # but we can see if CW got data.
    print(f"{cw_name.ljust(15)} | CW Average: {total_cw_avg:.2f}")


# Fetch Origin Data
res = requests.get(f"https://api.fastly.com/metrics/origins/services/{SERVICE_ID}?start={start_ts}&end={end_ts}&downsample=hour", headers=headers)
fastly_origin = res.json().get("data", [])

origin_fields = {
    "responses": "Responses",
    "status_2xx": "Status2xx",
    "status_3xx": "Status3xx",
    "status_4xx": "Status4xx",
    "status_5xx": "Status5xx"
}

print(f"\n--- AUDITING ORIGIN METRICS (Last 6 Hours) ---")
for fastly_key, cw_name in origin_fields.items():
    # Origin API groups by origin host, so we sum across all hosts for the given metric
    total_fastly = 0
    for point in fastly_origin:
        metrics = point.get("metrics", {})
        total_fastly += sum(metrics.get(fastly_key, []))

    cmd = f'aws cloudwatch get-metric-statistics --namespace Fastly/OriginInspector --metric-name {cw_name} --dimensions Name=FastlyServiceId,Value={SERVICE_ID} --start-time {start_iso} --end-time {end_iso} --period 3600 --statistics Sum'
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    cw_data = json.loads(out)
    total_cw = sum(dp['Sum'] for dp in cw_data['Datapoints'])
    
    diff = total_cw - total_fastly
    pct = (diff / total_fastly * 100) if total_fastly > 0 else 0
    print(f"{cw_name.ljust(15)} | Fastly: {total_fastly:<10} | CW: {total_cw:<10} | Diff: {diff:<6} ({pct:.2f}%)")

# Origin bandwidth
total_fastly_bw = 0
for point in fastly_origin:
    metrics = point.get("metrics", {})
    bw_vals = [hb + bb for hb, bb in zip(metrics.get("resp_header_bytes", []), metrics.get("resp_body_bytes", []))]
    total_fastly_bw += sum(bw_vals)

cmd = f'aws cloudwatch get-metric-statistics --namespace Fastly/OriginInspector --metric-name Bandwidth --dimensions Name=FastlyServiceId,Value={SERVICE_ID} --start-time {start_iso} --end-time {end_iso} --period 3600 --statistics Sum'
out = subprocess.check_output(cmd, shell=True).decode('utf-8')
total_cw_bw = sum(dp['Sum'] for dp in json.loads(out)['Datapoints'])

diff = total_cw_bw - total_fastly_bw
pct = (diff / total_fastly_bw * 100) if total_fastly_bw > 0 else 0
print(f"{'Bandwidth'.ljust(15)} | Fastly: {total_fastly_bw:<10} | CW: {total_cw_bw:<10} | Diff: {diff:<6} ({pct:.2f}%)")

# Latency Buckets
print("\n--- ORIGIN LATENCY BUCKETS (CW Totals) ---")
buckets = ["latency_0_to_1ms", "latency_1_to_5ms", "latency_5_to_10ms", "latency_10_to_50ms", "latency_50_to_100ms", "latency_100_to_250ms", "latency_250_to_500ms", "latency_500_to_1000ms", "latency_1000_to_5000ms", "latency_5000_to_10000ms", "latency_10000_to_60000ms", "latency_60000ms"]
for bucket in buckets:
    cw_name = ''.join(word.capitalize() for word in bucket.split('_'))
    cmd = f'aws cloudwatch get-metric-statistics --namespace Fastly/OriginInspector --metric-name {cw_name} --dimensions Name=FastlyServiceId,Value={SERVICE_ID} --start-time {start_iso} --end-time {end_iso} --period 3600 --statistics Sum'
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    total_cw = sum(dp['Sum'] for dp in json.loads(out)['Datapoints'])
    
    total_fastly = 0
    for point in fastly_origin:
        total_fastly += sum(point.get("metrics", {}).get(bucket, []))
        
    diff = total_cw - total_fastly
    pct = (diff / total_fastly * 100) if total_fastly > 0 else 0
    print(f"{cw_name.ljust(20)} | Fastly: {total_fastly:<8} | CW: {total_cw:<8} | Diff: {diff:<6} ({pct:.2f}%)")
