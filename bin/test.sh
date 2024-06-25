#!/bin/bash -e

# Export INFRAPOOL env vars for Cloud tests
export CONJUR_APPLIANCE_URL=$INFRAPOOL_CONJUR_APPLIANCE_URL
export CONJUR_ACCOUNT=conjur
export CONJUR_AUTHN_LOGIN=$INFRAPOOL_CONJUR_AUTHN_LOGIN
export CONJUR_AUTHN_TOKEN=$(echo "$INFRAPOOL_CONJUR_AUTHN_TOKEN" | base64 --decode)

echo "Conjur Cloud Appliance Url: $CONJUR_APPLIANCE_URL"
echo "Conjur Cloud Account: $CONJUR_ACCOUNT"
echo "Conjur Cloud Authn Login: $CONJUR_AUTHN_LOGIN"
echo "Conjur Cloud Authn Token: $CONJUR_AUTHN_TOKEN"