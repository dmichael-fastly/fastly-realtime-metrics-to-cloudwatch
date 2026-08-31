#!/bin/bash
set -e

echo "🗑️  Preparing to tear down Fastly Metrics to CloudWatch Infrastructure..."

# 1. Check AWS Credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Error: AWS credentials not found or expired. Please run 'aws configure' or export your AWS_ACCESS_KEY_ID."
    exit 1
fi

# 2. Run Terraform Destroy
echo "🔥 Running Terraform Destroy..."
cd terraform
terraform destroy
