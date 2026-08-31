# fastly-realtime-metrics-to-cloudwatch

See `README.md` for setup, architecture overview, and cost analysis.

## Conventions
- Use Python with `asyncio` and `aiohttp` for the Lambda function to fetch data for multiple services concurrently.
- All AWS infrastructure is defined in the `terraform/` directory.
- Use `boto3` for AWS interactions (CloudWatch PutMetricData).
- Keep Lambda execution time short to minimize costs.
- Store Fastly API tokens in AWS Secrets Manager, not in plaintext.

## Commands
- `./deploy.sh` - Package the Lambda and deploy the infrastructure via Terraform
- `./teardown.sh` - Destroy all Terraform-managed infrastructure
- `pytest` - Run Lambda unit tests (once added)
