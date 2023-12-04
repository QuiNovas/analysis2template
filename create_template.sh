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

if [ $? -ne 0 ]; then exit $?; fi

# Check if the template already exists
aws quicksight describe-template --aws-account-id "$account_id" --template-id "$template_id" &>/dev/null

if [ $? -eq 0 ]; then
    # Template exists, update it
    aws quicksight update-template \
        --aws-account-id "$account_id" \
        --template-id "$template_id" \
        --definition "$template_json" 1>/dev/null
else
    # Template doesn't exist, create it
    aws quicksight create-template \
        --aws-account-id "$account_id" \
        --template-id "$template_id" \
        --definition "$template_json" 1>/dev/null
fi

if [ $? -ne 0 ]; then exit $?; fi

while :; do
    response=$(aws quicksight describe-template --aws-account-id "$account_id" --template-id "$template_id")
    if [ $? -ne 0 ]; then exit $?; fi
    template=$(echo "$response" | jq .Template)
    if [ $? -ne 0 ]; then exit $?; fi
    status=$(echo "$template" | jq .Version.Status)
    if [ $? -ne 0 ]; then exit $?; fi
    
    if [[ "$status" =~ .*_SUCCESSFUL ]]; then
	    echo "$template"
        break
    elif [[ "$status" =~ .*_IN_PROGRESS ]]; then
	    sleep 1
        continue
    else
        echo "$template" | jq .Version.Errors
        exit 1
    fi
done
