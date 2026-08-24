#!/bin/bash
DOMAIN="https://${HOSTNAME}.themattwest.com"
USERNAME="test"

# Fetch 1-hour access token from Fence container
TOKEN=$(kubectl exec -c fence $(kubectl get pods | grep "^fence-deployment" | awk '{print $1}') -- \
  fence-create token-create \
  --scopes openid,user,fence,data,credentials,google_service_account \
  --type access_token \
  --exp 3600 \
  --username "$USERNAME" | tail -1 | tr -d '\r\n')

# Fetch CDIS credentials JSON and save to file
curl -s -X POST "${DOMAIN}/user/credentials/cdis/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -o credentials.json

echo "Credentials saved to credentials.json"
