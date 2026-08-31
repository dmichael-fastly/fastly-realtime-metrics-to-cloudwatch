resource "aws_cloudwatch_dashboard" "fastly_origin_metrics" {
  dashboard_name = "Fastly-Origin-Metrics"

  dashboard_body = jsonencode({
    variables = [
      {
        id           = "ServiceId"
        type         = "property"
        inputType    = "select"
        visible      = true
        label        = "Fastly Service"
        populateFrom = "FastlyServiceId"
        search       = "{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Responses\""
        property     = "FastlyServiceId"
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
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Responses\"', 'Sum', 60)", id = "origin_resp", label = "Total Origin Responses" }]
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
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Status_2xx\"', 'Sum', 60)", id = "o2xx", label = "2xx Success" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Status_3xx\"', 'Sum', 60)", id = "o3xx", label = "3xx Redirection" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Status_4xx\"', 'Sum', 60)", id = "o4xx", label = "4xx Client Error" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Status_5xx\"', 'Sum', 60)", id = "o5xx", label = "5xx Server Error" }]
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
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Resp_body_bytes\"', 'Sum', 60)", id = "obytes", label = "Body Bytes" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Resp_header_bytes\"', 'Sum', 60)", id = "ohbytes", label = "Header Bytes" }]
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
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_0_to_1ms\"', 'Sum', 60)", id = "l0", label = "0-1ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_1_to_5ms\"', 'Sum', 60)", id = "l1", label = "1-5ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_5_to_10ms\"', 'Sum', 60)", id = "l2", label = "5-10ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_10_to_50ms\"', 'Sum', 60)", id = "l3", label = "10-50ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_50_to_100ms\"', 'Sum', 60)", id = "l4", label = "50-100ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_100_to_250ms\"', 'Sum', 60)", id = "l5", label = "100-250ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_250_to_500ms\"', 'Sum', 60)", id = "l6", label = "250-500ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_500_to_1000ms\"', 'Sum', 60)", id = "l7", label = "500-1000ms" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_1000_to_5000ms\"', 'Sum', 60)", id = "l8", label = "1s-5s" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_5000_to_10000ms\"', 'Sum', 60)", id = "l9", label = "5s-10s" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_10000_to_60000ms\"', 'Sum', 60)", id = "l10", label = "10s-60s" }],
            [{ expression = "SEARCH('{Fastly/OriginInspector,FastlyServiceId} MetricName=\"Latency_60000ms\"', 'Sum', 60)", id = "l11", label = "60s+" }]
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
