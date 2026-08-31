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
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Responses", "FastlyServiceId", "$${ServiceId}", { id = "origin_resp", label = "Total Origin Responses ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Total Origin Responses (Per Service)"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Status_2xx", "FastlyServiceId", "$${ServiceId}", { id = "o2xx", label = "2xx Success ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Status_3xx", "FastlyServiceId", "$${ServiceId}", { id = "o3xx", label = "3xx Redirection ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Status_4xx", "FastlyServiceId", "$${ServiceId}", { id = "o4xx", label = "4xx Client Error ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Status_5xx", "FastlyServiceId", "$${ServiceId}", { id = "o5xx", label = "5xx Server Error ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Origin HTTP Status Families (Per Service)"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Resp_body_bytes", "FastlyServiceId", "$${ServiceId}", { id = "obytes", label = "Body Bytes ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Resp_header_bytes", "FastlyServiceId", "$${ServiceId}", { id = "ohbytes", label = "Header Bytes ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Origin Bandwidth (Bytes, Per Service)"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 8
        properties = {
          metrics = [
            ["Fastly/OriginInspector", "Latency_0_to_1ms", "FastlyServiceId", "$${ServiceId}", { id = "l0", label = "0-1ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_1_to_5ms", "FastlyServiceId", "$${ServiceId}", { id = "l1", label = "1-5ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_5_to_10ms", "FastlyServiceId", "$${ServiceId}", { id = "l2", label = "5-10ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_10_to_50ms", "FastlyServiceId", "$${ServiceId}", { id = "l3", label = "10-50ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_50_to_100ms", "FastlyServiceId", "$${ServiceId}", { id = "l4", label = "50-100ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_100_to_250ms", "FastlyServiceId", "$${ServiceId}", { id = "l5", label = "100-250ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_250_to_500ms", "FastlyServiceId", "$${ServiceId}", { id = "l6", label = "250-500ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_500_to_1000ms", "FastlyServiceId", "$${ServiceId}", { id = "l7", label = "500-1000ms ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_1000_to_5000ms", "FastlyServiceId", "$${ServiceId}", { id = "l8", label = "1s-5s ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_5000_to_10000ms", "FastlyServiceId", "$${ServiceId}", { id = "l9", label = "5s-10s ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_10000_to_60000ms", "FastlyServiceId", "$${ServiceId}", { id = "l10", label = "10s-60s ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/OriginInspector", "Latency_60000ms", "FastlyServiceId", "$${ServiceId}", { id = "l11", label = "60s+ ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "bar"
          stacked = true
          region  = var.aws_region
          title   = "Origin Latency Histogram (Per Service)"
          period  = 60
        }
      }
    ]
  })
}
