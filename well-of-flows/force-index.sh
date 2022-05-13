#!/bin/bash

STACKNAME=$1

if [ -z "$STACKNAME" ] ; then
	echo "Usage: $0 <STACKNAME>"
	exit 1
fi


FUNCTION_NAME=`aws cloudformation describe-stacks --stack-name ${STACKNAME} | jq -r '.Stacks[].Outputs[]|select(.OutputKey=="PartitionerFunction").OutputValue'`
EVENT_NAME=`aws cloudformation describe-stacks --stack-name ${STACKNAME} | jq -r '.Stacks[].Outputs[]|select(.OutputKey=="TriggerEvent").OutputValue'`

aws events list-targets-by-rule --rule $EVENT_NAME --query 'Targets[].Input' --output text > payload.json

echo "Invoking $FUNCTION_NAME"
aws lambda invoke --function-name $FUNCTION_NAME --payload fileb://payload.json output.json
cat output.json
echo
rm output.json
rm payload.json