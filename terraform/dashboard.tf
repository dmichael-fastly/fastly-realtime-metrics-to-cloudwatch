resource "aws_cloudwatch_dashboard" "fastly_metrics" {
  dashboard_name = "Fastly-RealTime-Metrics"

  dashboard_body = jsonencode({
    variables = [
      {
        id           = "ServiceId"
        type         = "property"
        inputType    = "select"
        visible      = true
        label        = "Fastly Service"
        populateFrom = "FastlyServiceId"
        search       = "{Fastly/RealTime,FastlyServiceId} MetricName=\"Requests\""
        property     = "FastlyServiceId"
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Requests\"', 'Sum', 60)", id = "reqs" }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Hits\"', 'Sum', 60)", id = "hits" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Misses\"', 'Sum', 60)", id = "misses" }]
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
            [{ expression = "SUM(hits) / (SUM(hits) + SUM(misses)) * 100", id = "hit_ratio", label = "Hit Ratio %", color = "#2ca02c" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Hits\"', 'Sum', 60)", id = "hits", visible = false }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Misses\"', 'Sum', 60)", id = "misses", visible = false }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Errors\"', 'Sum', 60)", id = "errs", color = "#d62728" }]
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
            [{ expression = "SUM(errs) / SUM(reqs) * 100", id = "error_rate", label = "Error Rate %", color = "#d62728" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Errors\"', 'Sum', 60)", id = "errs", visible = false }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Requests\"', 'Sum', 60)", id = "reqs", visible = false }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Resp_body_bytes\"', 'Sum', 60)", id = "body", label = "Body Bytes" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Resp_header_bytes\"', 'Sum', 60)", id = "headers", label = "Header Bytes" }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_2xx\"', 'Sum', 60)", id = "m2xx", label = "2xx Success" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_3xx\"', 'Sum', 60)", id = "m3xx", label = "3xx Redirection" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_4xx\"', 'Sum', 60)", id = "m4xx", label = "4xx Client Error" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_5xx\"', 'Sum', 60)", id = "m5xx", label = "5xx Server Error" }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_400\"', 'Sum', 60)", id = "m400", label = "400 Bad Request" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_401\"', 'Sum', 60)", id = "m401", label = "401 Unauthorized" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_403\"', 'Sum', 60)", id = "m403", label = "403 Forbidden" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_404\"', 'Sum', 60)", id = "m404", label = "404 Not Found" }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_500\"', 'Sum', 60)", id = "m500", label = "500 Internal Server Error" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_502\"', 'Sum', 60)", id = "m502", label = "502 Bad Gateway" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_503\"', 'Sum', 60)", id = "m503", label = "503 Service Unavailable" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Status_504\"', 'Sum', 60)", id = "m504", label = "504 Gateway Timeout" }]
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
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Compute_request_time_ms\"', 'Sum', 60)", id = "e_crt", label = "Compute Request Time (ms)" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Compute_execution_time_ms\"', 'Sum', 60)", id = "e_cet", label = "Compute Execution Time (ms)" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Miss_time\"', 'Sum', 60)", id = "e_mt", label = "Miss Time" }],
            [{ expression = "SEARCH('{Fastly/RealTime,FastlyServiceId} MetricName=\"Pass_time\"', 'Sum', 60)", id = "e_pt", label = "Pass Time" }]
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
          query   = "SOURCE '/aws/lambda/${aws_lambda_function.metrics_poller.function_name}' | fields @timestamp, @message | filter @message like /(?i)error|failed/ | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "System Health (Lambda Logs - Errors & Failures)"
          view    = "table"
        }
      }
    ]
  })
}

