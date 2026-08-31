# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-31

### Added
- **Dynamic Metrics Configuration:** Configure exactly which metrics are fetched and pushed to CloudWatch via `metrics.ini` to control AWS custom metric costs.
- **Origin Inspector Support:** Fetch and push real-time origin latency histograms and origin HTTP status codes.
- **Advanced CloudWatch Dashboards:** Automated Terraform deployment of comprehensive CloudWatch Dashboards using metric math (Hit Ratio, Error Rate) and stacked area charts for real-time visualization.
- **Configurable CloudWatch Alarms:** Pre-configured alarms for Edge 5xx spikes, Edge zero traffic, Origin 5xx spikes, and Origin high latency, with SNS email alerts.
- **Sub-Minute Polling:** Serverless asynchronous loop running on AWS Lambda triggered by AWS EventBridge Scheduler to fetch data every 5 seconds.
- **High-Resolution Metrics:** Optional support for pushing 1-second storage resolution metrics to CloudWatch.
- **Intelligent Payload Parsing:** Safely handles Fastly's sparse JSON payloads and accurately flattens host-grouped origin metrics.

### Changed
- Refactored architecture to use modern AWS EventBridge Scheduler instead of legacy CloudWatch Events rules.
- Upgraded CloudWatch dashboard to use body/header bytes instead of a singular bandwidth metric for better accuracy.

### Fixed
- Fixed an issue where the Fastly Origin Inspector API endpoint URL was returning 404s.
- Fixed a bug where nested objects in Fastly Real-Time edge payload (e.g. `miss_histogram`) could cause Lambda crashes during float conversion.
- Prevented data loss during standard 60s storage resolution aggregation by caching timestamps between sub-minute polls.
