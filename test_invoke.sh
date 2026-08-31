#!/bin/bash
set -e

echo "🚀 Manually invoking the Fastly Metrics Lambda..."
aws lambda invoke \
    --function-name fastly-realtime-metrics-poller \
    --payload '{}' \
    --cli-binary-format raw-in-base64-out \
    response.json

echo "✅ Invocation complete. Response:"
cat response.json
echo ""
echo "🧹 Cleaning up response file..."
rm response.json

echo "📊 Check your AWS CloudWatch Console under Metrics -> Custom Namespaces -> Fastly/RealTime to see the data!"
