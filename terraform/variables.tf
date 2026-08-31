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

variable "enable_origin_metrics" {
  description = "Enable fetching and pushing Fastly Origin Inspector metrics"
  type        = bool
  default     = false
}
