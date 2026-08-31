import re

for filename in ['terraform/dashboard.tf', 'terraform/origin_dashboard.tf']:
    with open(filename, 'r') as f:
        content = f.read()

    # Apply the variable correctly to the top of the file
    
    namespace = "Fastly/RealTime" if "origin" not in filename else "Fastly/OriginInspector"
    metric = "Requests" if namespace == "Fastly/RealTime" else "Responses"
    
    var_block = """  dashboard_body = jsonencode({
    variables = [
      {
        id           = "ServiceId"
        type         = "property"
        inputType    = "select"
        visible      = true
        label        = "Fastly Service"
        populateFrom = "FastlyServiceId"
        search       = "{NAMESPACE,FastlyServiceId} MetricName=\\"METRIC\\""
        property     = "FastlyServiceId"
      }
    ]
    widgets = ["""
    var_block = var_block.replace("NAMESPACE", namespace)
    var_block = var_block.replace("METRIC", metric)

    content = content.replace("  dashboard_body = jsonencode({\n    widgets = [", var_block)
    
    # We ALSO need to update the properties inside the labels from `$${PROP(\"Dim.FastlyServiceId\")}` to `$${PROP(\"FastlyServiceId\")}`
    content = content.replace('Dim.FastlyServiceId', 'FastlyServiceId')
    
    with open(filename, 'w') as f:
        f.write(content)

