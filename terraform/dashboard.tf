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
    widgets = [
      {
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
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Requests", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "reqs" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Total Requests (Per Service)"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 2
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Hits", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "hits" }],
            ["Fastly/RealTime", "Misses", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "misses" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "Cache Hits & Misses"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 2
        width  = 8
        height = 6
        properties = {
          metrics = [
            [{ expression = "(hits / (hits + misses)) * 100", id = "hit_ratio", label = "Hit Ratio %", color = "#2ca02c" }],
            ["Fastly/RealTime", "Hits", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "hits", visible = false }],
            ["Fastly/RealTime", "Misses", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "misses", visible = false }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Global Cache Hit Ratio (%)"
          period  = 60
          yAxis   = { left = { min = 0, max = 100 } }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Errors", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "errs", color = "#d62728" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Errors"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 8
        width  = 8
        height = 6
        properties = {
          metrics = [
            [{ expression = "(errs / reqs) * 100", id = "error_rate", label = "Error Rate %", color = "#d62728" }],
            ["Fastly/RealTime", "Errors", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "errs", visible = false }],
            ["Fastly/RealTime", "Requests", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "reqs", visible = false }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Global Error Rate (%)"
          period  = 60
          yAxis   = { left = { min = 0 } }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 8
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Bandwidth", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "bw", label = "Bandwidth ($${PROP(\"FastlyServiceId\")})" }],
            
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "Bandwidth Output (Bytes)"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Status_2xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m2xx", label = "2xx Success ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_3xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m3xx", label = "3xx Redirection ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_4xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m4xx", label = "4xx Client Error ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_5xx", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m5xx", label = "5xx Server Error ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "HTTP Status Families"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 14
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Status_400", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m400", label = "400 Bad Request ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_401", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m401", label = "401 Unauthorized ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_403", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m403", label = "403 Forbidden ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_404", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m404", label = "404 Not Found ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "4xx Breakdowns"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 14
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Status_500", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m500", label = "500 Internal Server Error ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_502", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m502", label = "502 Bad Gateway ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_503", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m503", label = "503 Service Unavailable ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Status_504", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "m504", label = "504 Gateway Timeout ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "5xx Breakdowns"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 20
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["Fastly/RealTime", "Compute_request_time_ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "e_crt", label = "Compute Request Time (ms) ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Compute_execution_time_ms", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "e_cet", label = "Compute Execution Time (ms) ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Miss_time", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "e_mt", label = "Miss Time ($${PROP(\"FastlyServiceId\")})" }],
            ["Fastly/RealTime", "Pass_time", "FastlyServiceId", "$${ServiceId}", { stat = "Sum", id = "e_pt", label = "Pass Time ($${PROP(\"FastlyServiceId\")})" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Edge Latency & Processing Times"
          period  = 60
        }
      },
      {
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
      }
    ]
  })
}

