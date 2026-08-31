# Fastly Real-Time Metrics to CloudWatch

## Architecture Notes
- Uses a "Serverless Polling Loop" pattern inside an AWS Lambda function triggered by AWS EventBridge.
- The Lambda polls Fastly's Real-Time API (Edge + Origin Inspector) asynchronously every `X` seconds.
- Uses Boto3 `PutMetricData` to push aggregated data into AWS CloudWatch under the `Fastly/RealTime` and `Fastly/OriginInspector` namespaces.
- Manages infrastructure natively through Terraform (`terraform/` directory).
- Fastly's data model is **sparse**; it only returns metric keys if they have non-zero values in that 1-second bucket. 

## Key Files
- `src/lambda_function.py`: The core Python polling logic, `aiohttp` requests, and AWS CloudWatch upload routing.
- `src/test_lambda_function.py`: Pytest suite using `pytest-asyncio` and `unittest.mock` to test parsing, flattening, sparse data handling, and cold starts.
- `metrics.ini`: Configurable manifest mapping Fastly metric IDs. Controls what gets pushed to CloudWatch to save on metric storage costs.
- `terraform/dashboard.tf`: Builds the Edge CloudWatch Dashboard with advanced stacked charts and hit ratio Metric Math.
- `terraform/origin_dashboard.tf`: Builds the Origin CloudWatch Dashboard with 12-bucket latency histograms.
- `terraform/alarms.tf`: Contains the dynamic `aws_cloudwatch_metric_alarm` definitions for 5xx Spikes, Zero Traffic, and High Latency.

## Commands
- **Deploy:** `./deploy.sh` (or `./deploy.sh -y` to auto-approve) - automatically zips the Python source and `metrics.ini`, then runs Terraform.
- **Teardown:** `./teardown.sh`
- **Run Tests:** `pytest src/test_lambda_function.py`
