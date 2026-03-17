#!/bin/bash
#####################################################################
# Heartbeat - VM sends "I'm alive" every 5 minutes
# Updates a GitHub Gist with sandbox_id + timestamp
# When VM is deleted, heartbeat stops, GitHub Action cleans up
#####################################################################

STATE_DIR="/opt/cloudshare-lab/state"
GIST_ID_FILE="/opt/cloudshare-lab/gist_id.txt"

# Read config
GITHUB_TOKEN=$(grep GITHUB_TOKEN /opt/cloudshare-lab/lab.env 2>/dev/null | cut -d= -f2)
GIST_ID=$(cat "$GIST_ID_FILE" 2>/dev/null)
SANDBOX_NAME=$(cat "$STATE_DIR/sandbox_name.txt" 2>/dev/null)
SANDBOX_ID=$(cat "$STATE_DIR/sandbox_id.txt" 2>/dev/null)

if [ -z "$GITHUB_TOKEN" ] || [ -z "$SANDBOX_ID" ]; then
    exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
CONTENT="${SANDBOX_NAME}|${SANDBOX_ID}|${TIMESTAMP}"

if [ -z "$GIST_ID" ]; then
    # Create new Gist
    RESPONSE=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/gists \
        -d "{
            \"description\": \"CloudShare Lab Heartbeats\",
            \"public\": false,
            \"files\": {
                \"${SANDBOX_NAME}.txt\": {
                    \"content\": \"${CONTENT}\"
                }
            }
        }")

    NEW_GIST_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    if [ -n "$NEW_GIST_ID" ]; then
        echo "$NEW_GIST_ID" > "$GIST_ID_FILE"
        GIST_ID="$NEW_GIST_ID"
    fi
else
    # Update existing Gist
    curl -s -X PATCH \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/gists/$GIST_ID" \
        -d "{
            \"files\": {
                \"${SANDBOX_NAME}.txt\": {
                    \"content\": \"${CONTENT}\"
                }
            }
        }" > /dev/null
fi
