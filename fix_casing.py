with open("src/lambda_function.py", "r") as f:
    content = f.read()

# Make sure we're strictly pushing capitalize() to CloudWatch since that's what the TF dashboard expects.
# Also print out exactly what metric names are being pushed so we can debug.

new_push = """
            for metric_name, value in summed_metrics.items():
                print(f"Pushing metric {metric_name.capitalize()} = {value}")
                metric_data.append({
                        '_namespace': namespace,
                        'MetricName': metric_name.capitalize(),
                        'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
                        'Timestamp': recorded_ts,
                        'Value': value,
                        'Unit': 'Count' if 'bytes' not in metric_name and metric_name != 'bandwidth' else 'Bytes',
                        'StorageResolution': 60
                    })
"""

old_push = """
            for metric_name, value in summed_metrics.items():
                metric_data.append({
                        '_namespace': namespace,
                        'MetricName': metric_name.capitalize(),
                        'Dimensions': [{'Name': 'FastlyServiceId', 'Value': service_id}],
                        'Timestamp': recorded_ts,
                        'Value': value,
                        'Unit': 'Count' if 'bytes' not in metric_name and metric_name != 'bandwidth' else 'Bytes',
                        'StorageResolution': 60
                    })
"""

content = content.replace(old_push, new_push)

with open("src/lambda_function.py", "w") as f:
    f.write(content)

