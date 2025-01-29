#!/bin/bash

start_instance() {
    # Request spot instance
    REQUEST_ID=$(aws ec2 request-spot-instances \
        --instance-count 1 \
        --type "one-time" \
        --launch-specification file://spot-spec.json \
        --query 'SpotInstanceRequests[0].SpotInstanceRequestId' \
        --output text)
    
    echo "Waiting for spot instance..."
    aws ec2 wait spot-instance-request-fulfilled --spot-instance-request-ids $REQUEST_ID

    # Get instance ID and wait for it to be running
    INSTANCE_ID=$(aws ec2 describe-spot-instance-requests \
        --spot-instance-request-ids $REQUEST_ID \
        --query 'SpotInstanceRequests[0].InstanceId' \
        --output text)
    
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID

    # Get DNS name
    EC2_DNS=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicDnsName' \
        --output text)

    # Update .env with new endpoint
    sed -i '' "/MODEL_ENDPOINT/d" .env
    echo "MODEL_ENDPOINT=http://${EC2_DNS}:8080" >> .env
    echo "Instance started at ${EC2_DNS}"
}

stop_instance() {
    # Terminate spot instance
    INSTANCE_ID=$(aws ec2 describe-instances \
        --filters "Name=instance-lifecycle,Values=spot" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text)
    
    if [ ! -z "$INSTANCE_ID" ]; then
        aws ec2 terminate-instances --instance-ids $INSTANCE_ID
        echo "Instance terminated"
    fi
}

case "$1" in
    start)
        start_instance
        ;;
    stop)
        stop_instance
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
esac 