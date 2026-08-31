locals {
  service_ids = compact([for s in split(",", var.fastly_service_ids) : trimspace(s)])
}

# -----------------------------------------------------------------------------
# SNS Topic for Email Alerts
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "alerts" {
  count = var.alert_email != "" ? 1 : 0
  name  = "fastly-metrics-alerts"
}

resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ==============================================================================
# EDGE ALARMS
# ==============================================================================

# -----------------------------------------------------------------------------
# Alarm: High Edge 5xx Error Rate (> 5% of traffic for 3 minutes)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "high_5xx_rate" {
  for_each = var.enable_alarms_edge ? toset(local.service_ids) : toset([])

  alarm_name          = "Fastly-Edge-5xx-Spike-${each.key}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 5
  alarm_description   = "Edge 5xx Server Errors exceed 5% of total requests over the last 3 minutes.\n\nInvestigate in Fastly: https://manage.fastly.com/observability/dashboard/system/overview/historic/${each.key}\nView CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards/dashboard/Fastly-RealTime-Metrics"
  treat_missing_data  = "notBreaching"
  
  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  # ok_actions    = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : [] # Uncomment to receive recovery emails

  metric_query {
    id          = "e1"
    expression  = "(m2 / m1) * 100"
    label       = "5xx Error Rate (%)"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      metric_name = "Requests"
      namespace   = "Fastly/RealTime"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }

  metric_query {
    id = "m2"
    metric {
      metric_name = "Status_5xx"
      namespace   = "Fastly/RealTime"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }
}

# -----------------------------------------------------------------------------
# Alarm: Zero Traffic (No requests for 5 consecutive minutes)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "zero_traffic" {
  for_each = var.enable_alarms_edge ? toset(local.service_ids) : toset([])

  alarm_name          = "Fastly-Edge-Zero-Traffic-${each.key}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5
  threshold           = 1
  alarm_description   = "Edge traffic has dropped to 0 for the last 5 minutes.\n\nInvestigate in Fastly: https://manage.fastly.com/observability/dashboard/system/overview/historic/${each.key}\nView CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards/dashboard/Fastly-RealTime-Metrics"
  treat_missing_data  = "breaching" # Missing data means no traffic!
  
  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  # ok_actions    = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : [] # Uncomment to receive recovery emails

  metric_name = "Requests"
  namespace   = "Fastly/RealTime"
  period      = 60
  statistic   = "Sum"
  
  dimensions = {
    FastlyServiceId = each.key
  }
}

# ==============================================================================
# ORIGIN ALARMS
# ==============================================================================

# -----------------------------------------------------------------------------
# Alarm: High Origin 5xx Error Rate (> 10% of origin traffic for 3 minutes)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "high_origin_5xx_rate" {
  for_each = var.enable_alarms_origin ? toset(local.service_ids) : toset([])

  alarm_name          = "Fastly-Origin-5xx-Spike-${each.key}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 10
  alarm_description   = "Origin 5xx Server Errors exceed 10% of origin responses over the last 3 minutes.\n\nInvestigate in Fastly: https://manage.fastly.com/observability/dashboard/system/overview/historic/${each.key}\nView CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards/dashboard/Fastly-RealTime-Metrics"
  treat_missing_data  = "notBreaching"
  
  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  # ok_actions    = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : [] # Uncomment to receive recovery emails

  metric_query {
    id          = "e1"
    expression  = "(m2 / m1) * 100"
    label       = "Origin 5xx Rate (%)"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      metric_name = "Responses"
      namespace   = "Fastly/OriginInspector"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }

  metric_query {
    id = "m2"
    metric {
      metric_name = "Status_5xx"
      namespace   = "Fastly/OriginInspector"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }
}

# -----------------------------------------------------------------------------
# Alarm: Origin High Latency (Slow requests > 5 seconds)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "origin_latency_spike" {
  for_each = var.enable_alarms_origin ? toset(local.service_ids) : toset([])

  alarm_name          = "Fastly-Origin-High-Latency-${each.key}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 100 # Alert if more than 100 requests take > 5s
  alarm_description   = "More than 100 origin requests experienced > 5 seconds of latency over the last 3 minutes.\n\nInvestigate in Fastly: https://manage.fastly.com/observability/dashboard/system/overview/historic/${each.key}\nView CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards/dashboard/Fastly-RealTime-Metrics"
  treat_missing_data  = "notBreaching"
  
  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  # ok_actions    = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : [] # Uncomment to receive recovery emails

  metric_query {
    id          = "e1"
    expression  = "m1 + m2 + m3"
    label       = "Slow Origin Requests (> 5s)"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      metric_name = "Latency_5000_to_10000ms"
      namespace   = "Fastly/OriginInspector"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }

  metric_query {
    id = "m2"
    metric {
      metric_name = "Latency_10000_to_60000ms"
      namespace   = "Fastly/OriginInspector"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }

  metric_query {
    id = "m3"
    metric {
      metric_name = "Latency_60000ms"
      namespace   = "Fastly/OriginInspector"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
    return_data = false
  }
}

# ==============================================================================
# SYSTEM HEALTH ALARMS
# ==============================================================================

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.enable_alarms_system ? 1 : 0

  alarm_name          = "Fastly-Metrics-Poller-Errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  alarm_description   = "Alerts if the Fastly metrics polling Lambda function encounters an execution error.\n\nView CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#logsV2:log-groups/log-group/$252Faws$252Flambda$252Ffastly-realtime-metrics-poller"
  treat_missing_data  = "notBreaching"

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  # ok_actions    = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : [] # Uncomment to receive recovery emails

  metric_name = "Errors"
  namespace   = "AWS/Lambda"
  period      = 60
  statistic   = "Sum"

  dimensions = {
    FunctionName = aws_lambda_function.metrics_poller.function_name
  }
}

# ==============================================================================
# ANOMALY DETECTION ALARMS
# ==============================================================================

resource "aws_cloudwatch_metric_alarm" "traffic_anomaly" {
  for_each = var.enable_alarms_anomaly ? toset(local.service_ids) : toset([])

  alarm_name          = "Fastly-Edge-Traffic-Anomaly-${each.key}"
  comparison_operator = "LessThanLowerOrGreaterThanUpperThreshold"
  evaluation_periods  = 3
  threshold_metric_id = "ad1"
  alarm_description   = "Machine learning anomaly detection for unexpected Fastly traffic drops or spikes.\n\nInvestigate in Fastly: https://manage.fastly.com/observability/dashboard/system/overview/historic/${each.key}\nView CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards/dashboard/Fastly-RealTime-Metrics"
  treat_missing_data  = "missing"

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  # ok_actions    = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : [] # Uncomment to receive recovery emails

  metric_query {
    id          = "ad1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 3)"
    label       = "Requests (Expected)"
    return_data = true
  }

  metric_query {
    id = "m1"
    return_data = true
    metric {
      metric_name = "Requests"
      namespace   = "Fastly/RealTime"
      period      = 60
      stat        = "Sum"
      dimensions = {
        FastlyServiceId = each.key
      }
    }
  }
}
