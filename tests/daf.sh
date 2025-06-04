#!/bin/bash

HOSTNAME="staging.openbraininstitute.org"
REALM_NAME="SBO"
CLIENT_ID="obi-entitysdk-auth"

DEVICE_CODE_RESPONSE=$(curl -s -X POST \
    -d "client_id=$CLIENT_ID" \
    "https://$HOSTNAME/auth/realms/$REALM_NAME/protocol/openid-connect/auth/device")

VERIFICATION_URL=$(echo $DEVICE_CODE_RESPONSE | jq -r '.verification_uri_complete')

echo Please open this url on a different tab: $VERIFICATION_URL

read -r -p "Press enter to continue:" CONTINUE

DEVICE_CODE=$(echo $DEVICE_CODE_RESPONSE | jq -r '.device_code')

curl -X POST \
    -d "grant_type=urn:ietf:params:oauth:grant-type:device_code" \
    -d "client_id=$CLIENT_ID" \
    -d "device_code=$DEVICE_CODE" \
    "https://$HOSTNAME/auth/realms/$REALM_NAME/protocol/openid-connect/token"
