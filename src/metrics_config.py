"""Single source of truth for metric naming, units, and metrics.ini parsing.

Shared by the Lambda runtime and scripts/export_config.py, which generates the
JSON consumed by Terraform — so the poller and the dashboards can never
disagree on a metric name.
"""
import configparser
import os
from typing import Any, Dict, List

DEFAULT_CONFIG = {
    'edge': {'enabled': 'true', 'metrics': 'requests, hits, misses, errors, bandwidth, status_2xx, status_3xx, status_4xx, status_5xx'},
    'origin': {'enabled': 'false', 'metrics': 'responses'}
}

def to_cloudwatch_name(metric_name: str) -> str:
    """Convert a Fastly snake_case metric id to the PascalCase name used in CloudWatch."""
    return ''.join(x.capitalize() for x in metric_name.lower().split('_'))

def get_metric_unit(metric_name: str) -> str:
    if 'bytes' in metric_name or metric_name == 'bandwidth':
        return 'Bytes'
    if metric_name.endswith('_ms'):
        return 'Milliseconds'
    if metric_name.endswith('_time'):
        return 'Seconds'
    return 'Count'

def parse_metrics_list(config: configparser.ConfigParser, section: str) -> List[str]:
    """Collect metric ids from the `metrics` key and every `metrics_extra*` key of a section, deduplicated in order."""
    metrics = []
    if config.has_section(section):
        for key, value in config.items(section):
            if key == 'metrics' or key.startswith('metrics_extra'):
                metrics.extend(m.strip() for m in value.split(',') if m.strip())
    return list(dict.fromkeys(metrics))

def load(path: str) -> Dict[str, Any]:
    """Parse a metrics.ini file (or the built-in defaults if it doesn't exist)."""
    config = configparser.ConfigParser()
    if os.path.exists(path):
        config.read(path)
    else:
        config.read_dict(DEFAULT_CONFIG)

    edge_enabled = config.getboolean('edge', 'enabled', fallback=True)
    origin_enabled = config.getboolean('origin', 'enabled', fallback=False)
    return {
        "edge": {"enabled": edge_enabled, "metrics": parse_metrics_list(config, 'edge') if edge_enabled else []},
        "origin": {"enabled": origin_enabled, "metrics": parse_metrics_list(config, 'origin') if origin_enabled else []}
    }

def to_terraform_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Shape a loaded config for Terraform: per section, enabled flag plus an id -> CloudWatch name map."""
    return {
        section: {
            "enabled": cfg["enabled"],
            "metrics": {metric_id: to_cloudwatch_name(metric_id) for metric_id in cfg["metrics"]}
        }
        for section, cfg in config.items()
    }
