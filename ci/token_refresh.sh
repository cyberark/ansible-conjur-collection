#!/bin/bash

# Refreshes Ansible Automation Hub token to prevent 30-day inactivity expiration
# Ref: https://console.redhat.com/ansible/automation-hub/

# Token is used to publish Conjur collection to Automation Hub
# Usage: summon -e publish ./ci/token_refresh.sh

set -euo pipefail

if [[ -z "${AUTOMATION_HUB_TOKEN:-}" ]]; then
  echo "AUTOMATION_HUB_TOKEN is not set. Cannot refresh token."
  exit 1
fi

echo "Refreshing Automation Hub token..."

curl -fsSL https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token \
  -d grant_type=refresh_token \
  -d client_id="cloud-services" \
  -d refresh_token="${AUTOMATION_HUB_TOKEN}" \
  --fail --silent --show-error --output /dev/null

echo "Automation Hub token refreshed successfully"