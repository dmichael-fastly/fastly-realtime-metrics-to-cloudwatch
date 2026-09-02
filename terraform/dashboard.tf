locals {
  # Widget definitions for the Edge dashboard. Each widget renders only the ids
  # present in metrics_config.json and is dropped entirely if none are — so the
  # dashboard always matches what the Lambda actually publishes.
  edge_widget_defs = [
    {
      title   = "Total Requests (Per Service)"
      x       = 0, y = 2, width = 8, height = 6
      stacked = false
      ids     = ["requests"]
      labels  = {}
      colors  = {}
    },
    {
      title   = "Cache Hits & Misses"
      x       = 8, y = 2, width = 8, height = 6
      stacked = true
      ids     = ["hits", "misses"]
      labels  = {}
      colors  = {}
    },
    {
      title   = "Errors"
      x       = 0, y = 8, width = 8, height = 6
      stacked = false
      ids     = ["errors"]
      labels  = {}
      colors  = { errors = "#d62728" }
    },
    {
      title   = "Bandwidth Output (Bytes)"
      x       = 16, y = 8, width = 8, height = 6
      stacked = true
      ids     = ["bandwidth"]
      labels  = {}
      colors  = {}
    },
    {
      title   = "HTTP Status Families"
      x       = 0, y = 14, width = 8, height = 6
      stacked = true
      ids     = ["status_2xx", "status_3xx", "status_4xx", "status_5xx"]
      labels = {
        status_2xx = "2xx Success"
        status_3xx = "3xx Redirection"
        status_4xx = "4xx Client Error"
        status_5xx = "5xx Server Error"
      }
      colors = {}
    },
    {
      title   = "4xx Breakdowns"
      x       = 8, y = 14, width = 8, height = 6
      stacked = true
      ids     = ["status_400", "status_401", "status_403", "status_404", "status_429", "status_499"]
      labels = {
        status_400 = "400 Bad Request"
        status_401 = "401 Unauthorized"
        status_403 = "403 Forbidden"
        status_404 = "404 Not Found"
        status_429 = "429 Too Many Requests"
        status_499 = "499 Client Closed Request"
      }
      colors = {}
    },
    {
      title   = "5xx Breakdowns"
      x       = 16, y = 14, width = 8, height = 6
      stacked = true
      ids     = ["status_500", "status_502", "status_503", "status_504"]
      labels = {
        status_500 = "500 Internal Server Error"
        status_502 = "502 Bad Gateway"
        status_503 = "503 Service Unavailable"
        status_504 = "504 Gateway Timeout"
      }
      colors = {}
    },
    {
      title   = "Edge Latency & Processing Times"
      x       = 0, y = 20, width = 24, height = 6
      stacked = false
      ids     = ["compute_request_time_ms", "compute_execution_time_ms", "miss_time", "pass_time"]
      labels = {
        compute_request_time_ms   = "Compute Request Time (ms)"
        compute_execution_time_ms = "Compute Execution Time (ms)"
        miss_time                 = "Miss Time"
        pass_time                 = "Pass Time"
      }
      colors = {}
    },
    {
      title   = "Edge Traffic Volume"
      x       = 0, y = 30, width = 12, height = 6
      stacked = false
      ids     = ["edge_requests", "edge_hit_requests", "edge_miss_requests"]
      labels = {
        edge_requests      = "Edge Requests"
        edge_hit_requests  = "Edge Hit Requests"
        edge_miss_requests = "Edge Miss Requests"
      }
      colors = {}
    },
    {
      title   = "Origin Shielding"
      x       = 12, y = 30, width = 12, height = 6
      stacked = false
      ids     = ["shield_fetches", "shield_hit_requests"]
      labels = {
        shield_fetches      = "Shield Fetches"
        shield_hit_requests = "Shield Hit Requests"
      }
      colors = {}
    },
    {
      title   = "Security & DDoS Protection"
      x       = 0, y = 36, width = 24, height = 6
      stacked = false
      ids     = ["ddos_protection_requests_detect_count", "ddos_protection_requests_mitigate_count", "ddos_protection_requests_allow_count"]
      labels = {
        ddos_protection_requests_detect_count   = "DDoS Detects"
        ddos_protection_requests_mitigate_count = "DDoS Mitigates"
        ddos_protection_requests_allow_count    = "DDoS Allows"
      }
      colors = {}
    },
  ]

  edge_data_widgets = [
    for w in local.edge_widget_defs : {
      type   = "metric"
      x      = w.x
      y      = w.y
      width  = w.width
      height = w.height
      properties = {
        metrics = [
          for id in w.ids : concat(
            ["Fastly/RealTime", local.edge_metrics[id], "FastlyServiceId", "$${ServiceId}"],
            [merge(
              { stat = "Sum", label = "${lookup(w.labels, id, local.edge_metrics[id])} ($${PROP(\"FastlyServiceId\")})" },
              lookup(w.colors, id, "") != "" ? { color = w.colors[id] } : {}
            )]
          ) if contains(keys(local.edge_metrics), id)
        ]
        view    = "timeSeries"
        stacked = w.stacked
        region  = var.aws_region
        title   = w.title
        period  = 60
      }
    } if length([for id in w.ids : id if contains(keys(local.edge_metrics), id)]) > 0
  ]

  edge_special_widgets = concat(
    [{
      type   = "text"
      x      = 0
      y      = 0
      width  = 24
      height = 2
      properties = {
        markdown = <<EOT
# Fastly Real-Time Edge Metrics
Monitoring edge requests, cache performance, errors, and bandwidth. See [Fastly Metrics Reference](https://www.fastly.com/documentation/reference/api/metrics-stats/realtime/).
EOT
      }
    }],
    contains(keys(local.edge_metrics), "hits") && contains(keys(local.edge_metrics), "misses") ? [{
      type   = "metric"
      x      = 16
      y      = 2
      width  = 8
      height = 6
      properties = {
        metrics = [
          [{ expression = "(hits / (hits + misses)) * 100", id = "hit_ratio", label = "Hit Ratio %", color = "#2ca02c" }],
          ["Fastly/RealTime", local.edge_metrics["hits"], "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "hits", visible = false }],
          ["Fastly/RealTime", local.edge_metrics["misses"], "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "misses", visible = false }]
        ]
        view    = "timeSeries"
        stacked = false
        region  = var.aws_region
        title   = "Global Cache Hit Ratio (%)"
        period  = 60
        yAxis   = { left = { min = 0, max = 100 } }
      }
    }] : [],
    contains(keys(local.edge_metrics), "errors") && contains(keys(local.edge_metrics), "requests") ? [{
      type   = "metric"
      x      = 8
      y      = 8
      width  = 8
      height = 6
      properties = {
        metrics = [
          [{ expression = "(errs / reqs) * 100", id = "error_rate", label = "Error Rate %", color = "#d62728" }],
          ["Fastly/RealTime", local.edge_metrics["errors"], "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "errs", visible = false }],
          ["Fastly/RealTime", local.edge_metrics["requests"], "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "reqs", visible = false }]
        ]
        view    = "timeSeries"
        stacked = false
        region  = var.aws_region
        title   = "Global Error Rate (%)"
        period  = 60
        yAxis   = { left = { min = 0 } }
      }
    }] : [],
    [{
      type   = "log"
      x      = 0
      y      = 99
      width  = 24
      height = 6
      properties = {
        query  = "SOURCE '/aws/lambda/${aws_lambda_function.metrics_poller.function_name}' | fields @timestamp, @message | filter @message like /(?i)error|failed/ | sort @timestamp desc | limit 20"
        region = var.aws_region
        title  = "System Health (Lambda Logs - Errors & Failures)"
        view   = "table"
      }
    }]
  )
}

resource "aws_cloudwatch_dashboard" "fastly_metrics" {
  dashboard_name = "Fastly-RealTime-Metrics"

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
    widgets = concat(local.edge_special_widgets, local.edge_data_widgets)
  })
}
