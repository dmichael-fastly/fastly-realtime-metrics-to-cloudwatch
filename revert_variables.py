import re

for filename in ['terraform/dashboard.tf', 'terraform/origin_dashboard.tf']:
    with open(filename, 'r') as f:
        content = f.read()

    # I'll revert the files entirely
    pass
