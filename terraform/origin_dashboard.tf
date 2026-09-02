locals {
  origin_widget_defs = [
    {
      title   = "Total Origin Responses (Per Service)"
      x       = 0, y = 0, width = 24, height = 6
      stacked = false
      ids     = ["responses"]
      labels  = { responses = "Total Origin Responses" }
    },
    {
      title   = "Origin HTTP Status Families (Per Service)"
      x       = 0, y = 6, width = 12, height = 6
      stacked = false
      ids     = ["status_2xx", "status_3xx", "status_4xx", "status_5xx"]
      labels = {
        status_2xx = "2xx Success"
        status_3xx = "3xx Redirection"
        status_4xx = "4xx Client Error"
        status_5xx = "5xx Server Error"
      }
    },
    {
      title   = "Origin Bandwidth (Bytes, Per Service)"
      x       = 12, y = 6, width = 12, height = 6
      stacked = false
      ids     = ["bandwidth"]
      labels  = {}
    },
    {
      title   = "Origin Latency Histogram (Per Service)"
      x       = 0, y = 12, width = 24, height = 8
      stacked = true
      ids = [
        "latency_0_to_1ms", "latency_1_to_5ms", "latency_5_to_10ms", "latency_10_to_50ms",
        "latency_50_to_100ms", "latency_100_to_250ms", "latency_250_to_500ms", "latency_500_to_1000ms",
        "latency_1000_to_5000ms", "latency_5000_to_10000ms", "latency_10000_to_60000ms", "latency_60000ms"
      ]
      labels = {
        latency_0_to_1ms         = "0-1ms"
        latency_1_to_5ms         = "1-5ms"
        latency_5_to_10ms        = "5-10ms"
        latency_10_to_50ms       = "10-50ms"
        latency_50_to_100ms      = "50-100ms"
        latency_100_to_250ms     = "100-250ms"
        latency_250_to_500ms     = "250-500ms"
        latency_500_to_1000ms    = "500-1000ms"
        latency_1000_to_5000ms   = "1s-5s"
        latency_5000_to_10000ms  = "5s-10s"
        latency_10000_to_60000ms = "10s-60s"
        latency_60000ms          = "60s+"
      }
    },
  ]

  origin_widgets = [
    for w in local.origin_widget_defs : {
      type   = "metric"
      x      = w.x
      y      = w.y
      width  = w.width
      height = w.height
      properties = {
        metrics = [
          for id in w.ids : concat(
            ["Fastly/OriginInspector", local.origin_metrics[id], "FastlyServiceId", "$${ServiceId}"],
            [{ stat = "Sum", label = "${lookup(w.labels, id, local.origin_metrics[id])} ($${PROP(\"FastlyServiceId\")})" }]
          ) if contains(keys(local.origin_metrics), id)
        ]
        view    = "timeSeries"
        stacked = w.stacked
        region  = var.aws_region
        title   = w.title
        period  = 60
      }
    } if length([for id in w.ids : id if contains(keys(local.origin_metrics), id)]) > 0
  ]
}

resource "aws_cloudwatch_dashboard" "fastly_origin_metrics" {
  # CloudWatch rejects a dashboard with zero widgets, so skip it entirely
  # when origin metrics are disabled
  count = length(local.origin_widgets) > 0 ? 1 : 0

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
    widgets = local.origin_widgets
  })
}
