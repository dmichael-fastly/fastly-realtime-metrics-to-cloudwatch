with open("src/lambda_function.py", "r") as f:
    content = f.read()

old_edge = """    if edge_enabled:
        edge_metrics.extend([m.strip() for m in config.get('edge', 'metrics', fallback='').split(',') if m.strip()])
        edge_metrics.extend([m.strip() for m in config.get('edge', 'metrics_extra', fallback='').split(',') if m.strip()])"""

new_edge = """    if edge_enabled:
        if config.has_section('edge'):
            for key, val in config.items('edge'):
                if key.startswith('metrics'):
                    edge_metrics.extend([m.strip() for m in val.split(',') if m.strip()])"""

old_origin = """    if origin_enabled:
        origin_metrics.extend([m.strip() for m in config.get('origin', 'metrics', fallback='').split(',') if m.strip()])
        origin_metrics.extend([m.strip() for m in config.get('origin', 'metrics_extra', fallback='').split(',') if m.strip()])"""

new_origin = """    if origin_enabled:
        if config.has_section('origin'):
            for key, val in config.items('origin'):
                if key.startswith('metrics'):
                    origin_metrics.extend([m.strip() for m in val.split(',') if m.strip()])"""

content = content.replace(old_edge, new_edge)
content = content.replace(old_origin, new_origin)

with open("src/lambda_function.py", "w") as f:
    f.write(content)
