#!/usr/bin/env python3
"""Generate terraform/metrics_config.json from metrics.ini.

Terraform builds the dashboards and alarms from this file, using the exact
CloudWatch metric names the Lambda publishes — the same Python code produces
both, so they cannot drift. Run automatically by deploy.sh; run manually
before `terraform plan`/`validate` outside of a deploy.

Falls back to metrics.ini.example when metrics.ini doesn't exist, mirroring
the Lambda packaging in deploy.sh.
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.metrics_config import load, to_terraform_config

def main() -> None:
    ini_path = os.path.join(REPO_ROOT, 'metrics.ini')
    if not os.path.exists(ini_path):
        ini_path = os.path.join(REPO_ROOT, 'metrics.ini.example')

    output_path = os.path.join(REPO_ROOT, 'terraform', 'metrics_config.json')
    config = to_terraform_config(load(ini_path))
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2, sort_keys=True)
        f.write('\n')

    edge, origin = config['edge'], config['origin']
    print(f"Wrote {os.path.relpath(output_path, REPO_ROOT)} from {os.path.basename(ini_path)}: "
          f"{len(edge['metrics'])} edge metrics (enabled={edge['enabled']}), "
          f"{len(origin['metrics'])} origin metrics (enabled={origin['enabled']})")

if __name__ == '__main__':
    main()
