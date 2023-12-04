#!/bin/bash

# Check if required arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <template_id> <template_json>"
    exit 1
fi

# Extract arguments
template_id="$1"
template_json="$2"

# Get the AWS account ID
account_id=$(aws sts get-caller-identity --query "Account" --output text)

# Check if the template already exists
aws quicksight describe-template --aws-account-id "$account_id" --template-id "$template_id" 2>/dev/null

if [ $? -eq 0 ]; then
    # Template exists, update it
    echo "Template already exists. Updating..."
    aws quicksight update-template \
        --aws-account-id "$account_id" \
        --template-id "$template_id" \
        --definition "$template_json"
else
    # Template doesn't exist, create it
    echo "Template does not exist. Creating..."
    aws quicksight create-template \
        --aws-account-id "$account_id" \
        --template-id "$template_id" \
        --definition "$template_json"
fi

while :; do
    template=$(aws quicksight describe-template --aws-account-id "$account_id" --template-id "$template_id")
    status=$(echo "$template" | jq .Template.Version.Status)
    if [ "$status" = "CREATION_SUCCESSFUL" || "$status" = "UPDATE_SUCCESSFUL" ]; then
        break
    elif [ "$status" = "CREATION_IN_PROGRESS" || "$status" = "UPDATE_IN_PROGRESS" ]; then
        sleep 1
        continue
    else
        echo "$template" | jq .Template.Version.Errors
        exit 1
done

echo "$template" | jq .Template
