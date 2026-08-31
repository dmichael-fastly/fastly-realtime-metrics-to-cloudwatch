# Fastly Real-Time Metrics to CloudWatch

This project deploys AWS infrastructure to fetch Fastly real-time metrics and ingest them into [AWS CloudWatch](https://aws.amazon.com/cloudwatch/). This allows you to leverage CloudWatch's powerful alerting, dashboarding, and analytics tools on your Fastly CDN data.

## Architecture

To meet the requirement of configurable, sub-minute data freshness (down to 1 second) while keeping costs extremely low, this project uses a serverless loop pattern:

1.  **[AWS EventBridge](https://aws.amazon.com/eventbridge/)** triggers an **[AWS Lambda](https://aws.amazon.com/lambda/)** function every 1 minute.
2.  The Python Lambda function reads a `POLL_INTERVAL_SECONDS` configuration and a `FASTLY_SERVICE_IDS` configuration (a comma-separated list of up to 10 services).
3.  Inside its 60-second execution window, the Lambda enters an asynchronous loop:
    *   Uses `asyncio` and `aiohttp` to fetch the latest metrics from the **[Fastly Real-Time Analytics API](https://www.fastly.com/documentation/reference/api/metrics-stats/realtime/)** (and optionally the **[Fastly Origin Inspector API](https://www.fastly.com/documentation/reference/api/metrics-stats/origin-inspector/real-time/)**) for all configured services *concurrently*.
    *   Pushes the aggregated metrics to **AWS CloudWatch** via the `boto3` `PutMetricData` API.
    *   Sleeps for the configured interval.
4.  Just as the 60 seconds are up, the Lambda exits, and EventBridge immediately triggers the next invocation.

Fastly API tokens are stored securely in **[AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)**. 
All infrastructure is managed via **[Terraform](https://www.terraform.io/)**.

---

## Configuration (`metrics.ini`)

You can control exactly which metrics are fetched and pushed to CloudWatch by editing the `metrics.ini` file in the root of the project. This allows you to manage your CloudWatch Custom Metric storage costs.

*   **Edge Metrics**: Enabled by default. You can track total requests, hits, errors, bandwidth, and specific HTTP status codes.
*   **Origin Metrics**: Enabled by default. If you have the Fastly Origin Inspector product enabled on your account, you can set `enabled = true` under `[origin]` to start tracking origin responses, origin status codes, and origin bandwidth.

---

## AWS Cost Analysis

The cost of running this project depends heavily on your configured `POLL_INTERVAL_SECONDS`.

AWS costs are driven by several factors:

**1. CloudWatch Custom Metrics (Storage):**
* Cost: $0.30 per metric / month.
* The default `metrics.ini` configuration explicitly tracks **23 core metrics per Fastly Service** (9 Edge metrics + 14 Origin metrics).
* If you uncomment the rest of the file to track all **94 Fastly metrics** provided in the template, it scales to **~$28.20 / month**.
* *(Note: The Fastly API actually exposes over 130+ metric fields. You can manually add any missing fields to the `metrics.ini` file if you need them).* 
* Cost for 1 Service (42 default metrics): **$12.60 / month**.
* Cost for 5 Services (42 metrics): **$63.00 / month**.
* Cost for 10 Services (42 metrics): **$126.00 / month**.
*(Note: Metric storage costs scale linearly based on how many metrics you enable in `metrics.ini` and how many Fastly Services you list in `FASTLY_SERVICE_IDS`)*

**2. CloudWatch `PutMetricData` API Requests:**
* By default, the Lambda batches data and pushes it every 5 seconds.
* `PutMetricData` costs $0.01 per 1,000 requests.
* 1 request every 5 seconds = 518,400 requests / month.
* Total API Cost: **~$5.18 / month**.
*(Note: If you track multiple Fastly services, they are batched together in the same API request, so this API cost is fixed and does NOT multiply per service!)*

**3. CloudWatch Alarms:**
* Cost: $0.10 per standard resolution alarm / month.
* By default, this project deploys 4 alarms **per Fastly Service** (Edge 5xx Spikes, Edge Zero Traffic, Origin 5xx Spikes, Origin Latency Spikes).
* Cost for 1 Service (4 alarms): **$0.40 / month**.
* Cost for 5 Services (20 alarms): **$2.00 / month**.
* Cost for 10 Services (40 alarms): **$4.00 / month**.
*(Note: You can easily toggle these alarms off or add your own in `terraform/variables.tf` and `terraform/alarms.tf`)*

**4. Lambda Compute Time:**
* Costs $0.0000166667 per GB-second.
* For a 60-second interval, the Lambda only runs for a couple of seconds per minute. 
* For any interval under 60 seconds, the Lambda runs continuously for the full minute to maintain the polling loop.

### High-Resolution Metrics
By default, the Lambda accumulates traffic data every 5 seconds and pushes it to standard 60-second CloudWatch resolution. This guarantees your traffic totals are 100% accurate while keeping costs low.

If you specifically want to see sub-minute granularity drawn on your CloudWatch charts, you can set `enable_high_resolution_metrics = true` in your `terraform.tfvars`. 
* **Storage Cost Impact**: $0 (Standard and High-Res metrics both cost $0.30/metric).
* **API Cost Impact**: $0 (Data is still batched).
* **Alarm Cost Impact**: **High**. If you create CloudWatch Alarms based on high-resolution data, they cost **$0.30 per alarm** (instead of $0.10 for standard alarms). Only enable this if you need sub-minute alerting!

### Estimated Monthly Costs by Polling Interval

*The following estimates assume you are using the **Recommended Setup (~22 metrics)** and are **not** using the AWS Free Tier. If your account qualifies for the Free Tier, your Lambda compute and initial CloudWatch requests will be largely free, bringing these costs down significantly.*

| Polling Interval | `PutMetricData` API Costs | Lambda Compute (128MB) | Base Costs (Metrics, Alarms, Logs) | **Estimated Total Cost / Month** |
| :--- | :--- | :--- | :--- | :--- |
| **1 second** | ~$25.92 / mo | ~$4.32 (ARM64 Continuous) | ~$7.70 | **~$37.94 / month** |
| **5 seconds** | ~$5.18 / mo | ~$4.32 (ARM64 Continuous) | ~$7.70 | **~$17.20 / month** |
| **10 seconds** | ~$2.59 / mo | ~$4.32 (ARM64 Continuous) | ~$7.70 | **~$14.61 / month** |
| **20 seconds** | ~$1.30 / mo | ~$4.32 (ARM64 Continuous) | ~$7.70 | **~$13.32 / month** |
| **30 seconds** | ~$0.86 / mo | ~$4.32 (ARM64 Continuous) | ~$7.70 | **~$12.88 / month** |
| **60 seconds (Default)** | ~$0.43 / mo | ~$4.32 (ARM64 Continuous) | ~$7.70 | **~$12.45 / month** |

**Cost Insights:**
*   **The 60-second drop-off:** Polling at 60 seconds is incredibly cheap (~$4.73/mo) because the Lambda function no longer has to run continuously; it wakes up, runs once, and immediately goes to sleep.
*   **The 1-second premium:** Polling at 1-second intervals generates a massive amount of CloudWatch API requests, which becomes the primary cost driver (~$35/mo).
*   **The sweet spot:** A 10-to-20 second interval provides excellent near real-time resolution for a flat ~$10-12/month.

## Getting Started

### Prerequisites
1.  **Fastly API Token:** You must generate a Fastly API token. 
    *   **Role/Scope:** The token only requires `global:read` access.
    *   **Service Access:** You can safely restrict the token to specific services, or allow access to "All Services".
2.  **AWS Credentials:** AWS CLI installed and authenticated.

### Deployment
We provide a wrapper script that automatically packages the Python Lambda dependencies and runs Terraform.

1.  Run the deployment script:
    ```bash
    ./deploy.sh
    ```
2.  Terraform will prompt you for the required values (or you can set them in `terraform/terraform.tfvars`):
    *   `fastly_api_key`: Your Fastly API token.
    *   `fastly_service_ids`: A comma-separated list of service IDs (e.g., `SU1Z0isxPaozGVKXdv0eY,1xyz2...`).
    *   `poll_interval_seconds`: How often to poll in seconds (e.g., `10`).

*(Alternatively, you can copy the provided `terraform/terraform.tfvars.example` file to `terraform/terraform.tfvars` and fill it out to supply these automatically and configure advanced options like Alert Emails).*

### Teardown
To cleanly remove all AWS resources (Lambda, IAM roles, EventBridge rules, and Secrets), run:
```bash
./teardown.sh
```

## License

This project is licensed under the **Apache License 2.0 with the Commons Clause v1.0**.

You are free to download, use, modify, and distribute this software for internal, personal, or academic purposes. However, you **may not sell** the software or provide it as a managed commercial service where its value derives entirely or substantially from the software's functionality. 

See the [LICENSE](LICENSE) file for the full license text.
