import boto3
import json
from datetime import datetime

def test_handleTable(detailed: bool = False):
    # Test parameters
    parent_entity = "Stanford"
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name='us-west-1')
        
        # 1. Setup the table through lambda handler
        event = {
            'action': 'setup',
            'parent_entity': parent_entity
        }
        
        # Invoke the actual AWS Lambda function
        response = lambda_client.invoke(
            FunctionName='handleTable',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        # Parse the response
        response_payload = json.loads(response['Payload'].read())
        
        print("\n=== Lambda Response Details ===")
        print(f"Status Code: {response.get('StatusCode')}")
        print(f"Function Error: {response.get('FunctionError', 'None')}")
        print(f"Executed Version: {response.get('ExecutedVersion', 'None')}")
        print("\nPayload:")
        print(json.dumps(response_payload, indent=2))
        
        # Check if Lambda function returned an error
        if response.get('FunctionError'):
            raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
            
        if response_payload.get('statusCode', 500) != 200:
            raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
            
        print("✅ handleTable.py successful (1/1)")
        if detailed:
            print("        - ✅ Table setup successful")
        
    except Exception as e:
        if f"Table {table_name} already exists" in str(e):
            print("✅ handleTable.py successful (1/1)")
            if detailed:
                print("        - ✅ Table already exists")
        else:
            print("❌ Error during table creation")
            if detailed:
                print("        - ❌ Table setup failed")
            raise

if __name__ == "__main__":
    test_handleTable(detailed=True)  # Can be set to False for simplified output 