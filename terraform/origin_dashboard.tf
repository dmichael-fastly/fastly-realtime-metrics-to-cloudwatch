resource "aws_cloudwatch_dashboard" "fastly_origin_metrics" {
  dashboard_name = "Fastly-Origin-Metrics"

  dashboard_body = jsonencode({
    variables = [
      {
        id        = "ServiceId"
        type      = "property"
        inputType = "select"
        visible   = true
        label     = "Fastly Service"
        property  = "FastlyServiceId"
        values    = [for id, name in local.service_map : { label = name, value = id }]
      }
    ]
    widgets = flatten([
      local.origin_resp ? [{
        type   = "metric"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Responses", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "origin_resp", label = "Total Origin Responses ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Total Origin Responses (Per Service)"
          period  = 60
        }
      }] : [],
      local.origin_status ? [{
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Status2xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "o2xx", label = "2xx Success ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Status3xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "o3xx", label = "3xx Redirection ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Status4xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "o4xx", label = "4xx Client Error ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Status5xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "o5xx", label = "5xx Server Error ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Origin HTTP Status Families (Per Service)"
          period  = 60
        }
      }] : [],
      local.origin_bw ? [{
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Bandwidth", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "obw", label = "Bandwidth ($${PROP(\"FastlyServiceId\")})" }],

          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Origin Bandwidth (Bytes, Per Service)"
          period  = 60
        }
      }] : [],
      local.origin_latency ? [{
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 8
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Latency0To1ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l0", label = "0-1ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency1To5ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l1", label = "1-5ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency5To10ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l2", label = "5-10ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency10To50ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l3", label = "10-50ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency50To100ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l4", label = "50-100ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency100To250ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l5", label = "100-250ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency250To500ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l6", label = "250-500ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency500To1000ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l7", label = "500-1000ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency1000To5000ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l8", label = "1s-5s ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency5000To10000ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l9", label = "5s-10s ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency10000To60000ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l10", label = "10s-60s ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency60000ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "l11", label = "60s+ ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "Origin Latency Histogram (Per Service)"
          period  = 60
        }
      }] : [],
    ])
  })
}