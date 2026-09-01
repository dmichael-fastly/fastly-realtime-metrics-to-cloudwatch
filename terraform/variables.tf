variable "aws_region" {
  description = "The AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "fastly_api_key" {
  description = "Fastly API key with permissions to read Real-Time Analytics"
  type        = string
  sensitive   = true
}

variable "fastly_service_ids" {
  description = "Comma-separated list of Fastly Service IDs to monitor (max 10)"
  type        = string
}

variable "poll_interval_seconds" {
  description = "How often the Lambda should poll Fastly within its 60-second window (e.g., 5)"
  type        = number
  default     = 5
}

variable "enable_high_resolution_metrics" {
  description = "Enable 1-second storage resolution in CloudWatch. Warning: can significantly increase CloudWatch Alarm costs if used."
  type        = bool
  default     = false
}

variable "alert_email" {
  description = "Email address to send CloudWatch Alarm notifications to. Leave blank to disable email alerts."
  type        = string
  default     = ""
}

# ==============================================================================
# ALARM CONFIGURATIONS
# ==============================================================================

variable "enable_alarms_edge" {
  description = "Enable default CloudWatch Alarms for Edge Metrics (5xx Spikes, Zero Traffic)"
  type        = bool
  default     = true
}

variable "enable_alarms_origin" {
  description = "Enable default CloudWatch Alarms for Origin Metrics (Latency Spikes, Error Spikes)"
  type        = bool
  default     = true
}

variable "enable_alarms_anomaly" {
  description = "Enable CloudWatch Machine Learning Anomaly Detection Alarms for traffic drops or spikes"
  type        = bool
  default     = true
}

variable "enable_alarms_system" {
  description = "Enable System Health Alarms (e.g., Lambda execution errors)"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to keep CloudWatch Logs for the Lambda function"
  type        = number
  default     = 7
}


locals {
  # Only consider uncommented lines, so a commented-out metric doesn't render an empty widget
  metrics_ini = join("\n", [
    for line in split("\n", file("${path.module}/../metrics.ini")) : line
    if !startswith(trimspace(line), "#") && !startswith(trimspace(line), ";")
  ])
  edge_reqs      = length(regexall("requests", local.metrics_ini)) > 0
  edge_hits      = length(regexall("hits", local.metrics_ini)) > 0
  edge_misses    = length(regexall("misses", local.metrics_ini)) > 0
  edge_errors    = length(regexall("errors", local.metrics_ini)) > 0
  edge_bandwidth = length(regexall("bandwidth", local.metrics_ini)) > 0
  edge_status    = length(regexall("status_2xx", local.metrics_ini)) > 0
  edge_4xx       = length(regexall("status_400", local.metrics_ini)) > 0
  edge_5xx       = length(regexall("status_500", local.metrics_ini)) > 0
  edge_compute   = length(regexall("compute_request_time_ms", local.metrics_ini)) > 0

  origin_resp    = length(regexall("responses", local.metrics_ini)) > 0
  origin_bw      = length(regexall("bandwidth", local.metrics_ini)) > 0
  origin_status  = length(regexall("status_2xx", local.metrics_ini)) > 0
  origin_latency = length(regexall("latency_0_to_1ms", local.metrics_ini)) > 0

  edge_volume   = length(regexall("edge_requests", local.metrics_ini)) > 0
  edge_shield   = length(regexall("shield_fetches", local.metrics_ini)) > 0
  edge_security = length(regexall("ddos_protection_requests_detect_count", local.metrics_ini)) > 0
}
