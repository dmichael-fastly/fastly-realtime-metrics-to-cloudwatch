
terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

locals {
  service_ids = compact([for s in split(",", var.fastly_service_ids) : trimspace(s)])
}

data "http" "fastly_services" {
  for_each = toset(local.service_ids)

  url = "https://api.fastly.com/service/${each.key}"
  request_headers = {
    Fastly-Key = var.fastly_api_key
    Accept     = "application/json"
  }
}

locals {
  service_map = {
    for id in local.service_ids : id => "${jsondecode(data.http.fastly_services[id].response_body).name} (${id})"
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# 1. Store Fastly API Key in Secrets Manager
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "fastly_api_key" {
  name_prefix = "fastly-realtime-metrics-api-key"
  description = "API key for Fastly Real-Time Analytics Lambda"
}

resource "aws_secretsmanager_secret_version" "fastly_api_key_value" {
  secret_id     = aws_secretsmanager_secret.fastly_api_key.id
  secret_string = var.fastly_api_key
}

# -----------------------------------------------------------------------------
# 2. IAM Role for Lambda
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name_prefix        = "fastly-metrics-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# Basic execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy to read secret and write custom metrics
data "aws_iam_policy_document" "lambda_policy" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.fastly_api_key.arn]
  }

  statement {
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values = [
        "Fastly/RealTime",
        "Fastly/OriginInspector"
      ]
    }
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name_prefix = "fastly-metrics-lambda-policy"
  policy      = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# -----------------------------------------------------------------------------
# 3. Lambda Function
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/fastly-realtime-metrics-poller"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "metrics_poller" {
  function_name    = "fastly-realtime-metrics-poller"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  filename         = "${path.module}/../lambda.zip"
  source_code_hash = fileexists("${path.module}/../lambda.zip") ? filebase64sha256("${path.module}/../lambda.zip") : ""

  # The Lambda needs to run for the full minute
  timeout     = 60
  memory_size = 256

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs
  ]

  environment {
    variables = {
      SECRET_ARN                     = aws_secretsmanager_secret.fastly_api_key.arn
      FASTLY_SERVICE_IDS             = var.fastly_service_ids
      POLL_INTERVAL_SECONDS          = tostring(var.poll_interval_seconds)
      ENABLE_HIGH_RESOLUTION_METRICS = tostring(var.enable_high_resolution_metrics)
    }
  }
}

# -----------------------------------------------------------------------------
# 4. EventBridge Scheduler (Modern approach)
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler_role" {
  name_prefix        = "fastly-metrics-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "scheduler_policy" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.metrics_poller.arn]
  }
}

resource "aws_iam_policy" "scheduler_policy" {
  name_prefix = "fastly-metrics-scheduler-policy"
  policy      = data.aws_iam_policy_document.scheduler_policy.json
}

resource "aws_iam_role_policy_attachment" "scheduler_policy_attachment" {
  role       = aws_iam_role.scheduler_role.name
  policy_arn = aws_iam_policy.scheduler_policy.arn
}

resource "aws_scheduler_schedule" "every_minute" {
  name        = "fastly-metrics-every-minute"
  description = "Fires every minute to trigger the Fastly metrics poller"
  group_name  = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(1 minutes)"
  state               = "ENABLED"

  target {
    arn      = aws_lambda_function.metrics_poller.arn
    role_arn = aws_iam_role.scheduler_role.arn
  }
}
