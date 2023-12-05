#!/bin/bash

# Exit if any of the intermediate steps fail
set -e


# Extract "id" and "definition" arguments from the input into
# template_id and definition shell variables.
# jq will ensure that the values are properly quoted
# and escaped for consumption by the shell.
eval "$(jq -r '@sh "template_id=\(.template_id) definition_path=\(.definition_path)"')"

definition=$(cat "$definition_path")

# Get the AWS account ID
account_id=$(aws sts get-caller-identity --query "Account" --output text)

set +e

# Check if the template already exists
aws quicksight describe-template --aws-account-id "$account_id" --template-id "$template_id" &>/dev/null

result=$?
set -e

if [ $result -eq 0 ]; then
    # Template exists, update it
    aws quicksight update-template \
        --aws-account-id "$account_id" \
        --template-id "$template_id" \
        --definition "$definition" 1>/dev/null
else
    # Template doesn't exist, create it
    aws quicksight create-template \
        --aws-account-id "$account_id" \
        --template-id "$template_id" \
        --definition "$definition" 1>/dev/null
fi

# Loop until the creation/update is successful or fails
while :; do
    response=$(aws quicksight describe-template --aws-account-id "$account_id" --template-id "$template_id")
    template=$(echo "$response" | jq .Template)
    status=$(echo "$template" | jq .Version.Status)
    
    if ! [[ "$status" =~ .*_IN_PROGRESS ]]; then break; fi
    sleep 1
done

if [[ "$status" =~ .*_SUCCESSFUL ]]; then
    echo "$template" | jq 'del(.Version)'
else
    echo "$template" | jq .Version.Errors 1>&2
    exit 1
fi
