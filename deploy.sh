#!/bin/bash
set -e

echo "🚀 Preparing Fastly Metrics to CloudWatch Deployment..."

# 1. Check AWS Credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Error: AWS credentials not found or expired. Please run 'aws configure' or export your AWS_ACCESS_KEY_ID."
    exit 1
fi

# 2. Package the Python Lambda
echo "📦 Packaging Python Lambda function (Linux ARM64)..."
rm -rf package lambda.zip
mkdir -p package
pip install --platform manylinux2014_aarch64 --target=package/ --implementation cp --python-version 3.12 --only-binary=:all: --upgrade -r src/requirements.txt > /dev/null 2>&1
cp src/lambda_function.py package/
if [ -f "metrics.ini" ]; then
    cp metrics.ini package/
fi
cd package
zip -r ../lambda.zip . > /dev/null 2>&1
cd ..
rm -rf package
echo "✅ Lambda packaged successfully (lambda.zip)."

# Check for auto-approve flag
AUTO_APPROVE=""
if [ "$1" = "-y" ] || [ "$1" = "--auto-approve" ]; then
    AUTO_APPROVE="-auto-approve"
    echo "⚡ Auto-approve mode enabled."
fi

# 3. Run Terraform
echo "🏗️  Running Terraform..."
cd terraform
terraform init
echo ""
if [ -z "$AUTO_APPROVE" ]; then
    echo "📝 Terraform will now ask for your configuration if you haven't provided a terraform.tfvars file."
    echo "You can also hit Ctrl+C and create a terraform.tfvars file with your variables."
    echo ""
fi
terraform apply $AUTO_APPROVE
