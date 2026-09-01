with open("src/lambda_function.py", "r") as f:
    content = f.read()

new_hrm = """
        if enable_hrm:
            for d in unseen_data:
                recorded_ts = d.get("recorded", int(time.time()))
                aggregated = flatten_metrics(d.get("aggregated", {}))
                for metric_name in metrics_to_track:
                    print(f"Pushing HRM metric {metric_name.capitalize()} = {aggregated.get(metric_name, 0.0)}")
                    metric_data.append({
                            '_namespace': namespace,
                            'MetricName': metric_name.capitalize(),
                            'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
                            'Timestamp': recorded_ts,
                            'Value': aggregated.get(metric_name, 0.0),
                            'Unit': 'Count' if 'bytes' not in metric_name and metric_name != 'bandwidth' else 'Bytes',
                            'StorageResolution': 1
                        })
"""

old_hrm = """
        if enable_hrm:
            for d in unseen_data:
                recorded_ts = d.get("recorded", int(time.time()))
                aggregated = flatten_metrics(d.get("aggregated", {}))
                for metric_name in metrics_to_track:
                    metric_data.append({
                            '_namespace': namespace,
                            'MetricName': metric_name.capitalize(),
                            'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
                            'Timestamp': recorded_ts,
                            'Value': aggregated.get(metric_name, 0.0),
                            'Unit': 'Count' if 'bytes' not in metric_name and metric_name != 'bandwidth' else 'Bytes',
                            'StorageResolution': 1
                        })
"""

content = content.replace(old_hrm, new_hrm)

with open("src/lambda_function.py", "w") as f:
    f.write(content)
