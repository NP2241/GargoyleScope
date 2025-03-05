#!/bin/bash

echo "🗑️ Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name gargoylescope

echo "⏳ Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name gargoylescope

echo "✅ Cleanup complete - run ./deploy.sh to redeploy" 