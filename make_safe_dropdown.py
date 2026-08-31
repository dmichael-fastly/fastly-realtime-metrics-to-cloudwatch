import re

for filename in ['terraform/dashboard.tf', 'terraform/origin_dashboard.tf']:
    with open(filename, 'r') as f:
        content = f.read()

    # The safe way to do this is with pattern variables and a wildcard.
    # CloudWatch doesn't care about the search if we just use a pattern variable and let them type a ServiceID
    # Or, we just use a wildcard variable.
    # Wait, earlier I tried:
    # variables = [{ type = "pattern", value = "*", label = "Fastly Service" ... }]
    
    # Or, maybe the easiest way is to use property, but just rely on `value="cVnu9mYB3Cvmob3lsqjQU3"` for now? No, we don't know the service ID dynamically.
    
    # Let's try the pattern variable correctly:
    var_block = """  dashboard_body = jsonencode({
    variables = [
      {
        id           = "ServiceId"
        type         = "pattern"
        inputType    = "input"
        visible      = true
        value        = "*"
        label        = "Fastly Service (ID or *)"
      }
    ]
    widgets = ["""

    content = content.replace("  dashboard_body = jsonencode({\n    widgets = [", var_block)

    # Convert the generic SEARCH expressions to specifically inject the variable into the metric name
    # e.g., SEARCH('{Fastly/RealTime,FastlyServiceId} FastlyServiceId=\"$${ServiceId}\" MetricName=\"Requests\"' ...
    
    # The current code in HEAD~1 doesn't have the injection.
    
    namespace = "Fastly/RealTime" if "origin" not in filename else "Fastly/OriginInspector"
    
    content = content.replace(f"SEARCH('{{{namespace},FastlyServiceId}} MetricName=", f"SEARCH('{{{namespace},FastlyServiceId}} FastlyServiceId=\"$${{ServiceId}}\" MetricName=")

    with open(filename, 'w') as f:
        f.write(content)

