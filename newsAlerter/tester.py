import boto3
import json
from datetime import datetime

def test_handleTable(detailed: bool = False, test_email: str = "neilpendyala@gmail.com"):
    """
    Test handleTable lambda functionality
    
    Args:
        detailed (bool): Whether to show detailed test output
        test_email (str): Email to use for testing email list functionality
    """
    # Test parameters
    parent_entity = "Stanford"
    table_name = f"{parent_entity}_TrackedEntities"
    test_entity = "Rangoon Ruby"
    successful_steps = 0
    status_messages = []
    total_steps = 9  # Default to full test suite
    
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name='us-west-1')
        
        # 1. Setup the table through lambda handler
        event = {
            'action': 'setup',
            'parent_entity': parent_entity
        }
        
        # Invoke the actual AWS Lambda function
        event_json = json.dumps(event).encode('utf-8')
        response = lambda_client.invoke(
            FunctionName='handleTable',
            InvocationType='RequestResponse',
            Payload=event_json
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('FunctionError'):
            raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
            
        if response_payload.get('statusCode', 500) != 200:
            raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
            
        successful_steps += 1
        status_messages.append("        - ✅ Table created successfully")
        
        # 2. Add entity to table
        event = {
            'action': 'add',
            'parent_entity': parent_entity,
            'entities': [test_entity]
        }
        
        event_json = json.dumps(event).encode('utf-8')
        response = lambda_client.invoke(
            FunctionName='handleTable',
            InvocationType='RequestResponse',
            Payload=event_json
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('FunctionError'):
            raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
            
        if response_payload.get('statusCode', 500) != 200:
            raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
        
        successful_steps += 1
        status_messages.append(f"        - ✅ Added entity: {test_entity}")
        
        # 3. List entities
        event = {
            'action': 'list',
            'parent_entity': parent_entity
        }
        
        event_json = json.dumps(event).encode('utf-8')
        response = lambda_client.invoke(
            FunctionName='handleTable',
            InvocationType='RequestResponse',
            Payload=event_json
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('FunctionError'):
            raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
            
        if response_payload.get('statusCode', 500) != 200:
            raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
        
        # Verify the entity is in the list
        entities_list = json.loads(response_payload.get('body', '{}')).get('entities', [])
        if test_entity not in entities_list:
            raise Exception(f"Added entity {test_entity} not found in list")
        
        successful_steps += 1
        status_messages.append(f"        - ✅ Listing successful: {entities_list}")
        
        # 4. Check completion status
        try:
            # Add entity with analysis and completed=True
            dummy_analysis = {
                'article': {
                    'title': 'Regular Update',
                    'url': 'http://example.com/regular/1',
                    'snippet': 'Standard business update.'
                },
                'analysis': {
                    'sentiment': 'neutral',
                    'summary': 'Regular business operations update.',
                    'important': False
                }
            }
            
            event = {
                'action': 'add',
                'parent_entity': parent_entity,
                'entities': [test_entity],
                'analysis': dummy_analysis,
                'completed': True
            }
            
            event_json = json.dumps(event).encode('utf-8')
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=event_json
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                
            if response_payload.get('statusCode', 500) != 200:
                raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
            
            successful_steps += 1
            status_messages.append(f"        - ✅ Added entity with analysis data and completed=True")
        except Exception as e:
            print("❌ Error adding entity with analysis")
            if detailed:
                print(f"        - ❌ Failed to add entity with analysis: {str(e)}")
            print(f"❌ handleTable.py failed ({successful_steps}/6)")
        
        # Try to list entities
        try:
            event = {
                'action': 'list',
                'parent_entity': parent_entity
            }
            
            event_json = json.dumps(event).encode('utf-8')
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=event_json
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                
            if response_payload.get('statusCode', 500) != 200:
                raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
                
            # Verify the entity is in the list
            entities_list = json.loads(response_payload.get('body', '{}')).get('entities', [])
            if test_entity not in entities_list:
                raise Exception(f"Added entity {test_entity} not found in list")
                
            successful_steps += 1
            status_messages.append(f"        - ✅ Listing successful: {entities_list}")
            
        except Exception as e:
            status_messages.append(f"        - ❌ Failed to list entities")
            print(f"❌ handleTable.py failed ({successful_steps}/6)")
            if detailed:
                for msg in status_messages:
                    print(msg)
            raise
        
        # 5. Delete entity and check completion status
        try:
            event = {
                'action': 'delete',
                'parent_entity': parent_entity,
                'entities': [test_entity]
            }
            
            event_json = json.dumps(event).encode('utf-8')
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=event_json
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                
            if response_payload.get('statusCode', 500) != 200:
                raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
            
            status_messages.append(f"        - ✅ Deleted entity: {test_entity}")
            successful_steps += 1

            # Set up email list
            event = {
                'action': 'setup_email_list',
                'parent_entity': parent_entity,
                'initial_emails': [test_email]
            }
            
            event_json = json.dumps(event).encode('utf-8')
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=event_json
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                
            if response_payload.get('statusCode', 500) != 200:
                raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
            
            successful_steps += 1
            status_messages.append(f"        - ✅ Email list setup verified (setup_email_list)")

            # Verify email list was set up by getting it
            event = {
                'action': 'get_email_list',
                'parent_entity': parent_entity
            }
            
            event_json = json.dumps(event).encode('utf-8')
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=event_json
            )
            
            response_payload = json.loads(response['Payload'].read())
            email_list = json.loads(response_payload.get('body', '{}')).get('email_list', [])
            
            if test_email not in email_list:
                raise Exception(f"Email {test_email} not found in email list")
            
            successful_steps += 1
            status_messages.append(f"        - ✅ Retrieved email list: {email_list} (get_email_list)")

            # Check completion status
            event = {
                'action': 'checkCompleted',
                'parent_entity': parent_entity
            }
            
            event_json = json.dumps(event).encode('utf-8')
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=event_json
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                
            if response_payload.get('statusCode', 500) != 200:
                raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")

            completion_status = json.loads(response_payload.get('body', '{}')).get('all_completed', True)
            if completion_status:
                raise Exception("Expected completion status to be False")
            
            successful_steps += 1
            status_messages.append("        - ✅ Verified completion status is False")

        except Exception as e:
            status_messages.append(f"        - ❌ Failed to setup or verify email list: {str(e)}")
            print(f"❌ handleTable.py failed ({successful_steps}/7)")
            if detailed:
                for msg in status_messages:
                    print(msg)
            raise
        finally:
            if detailed:
                for msg in status_messages:
                    print(msg)

    except Exception as e:
        if f"Table {table_name} already exists" in str(e):
            successful_steps += 1
            status_messages.append("        - ✅ Table already exists (setup)")
            total_steps = 7  # Updated to include get_email_list test
            
            # Continue with adding entity even if table exists
            try:
                # Basic add operation
                event = {
                    'action': 'add',
                    'parent_entity': parent_entity,
                    'entities': [test_entity]
                }
                
                event_json = json.dumps(event).encode('utf-8')
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=event_json
                )
                
                response_payload = json.loads(response['Payload'].read())
                
                if response.get('FunctionError'):
                    raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                    
                if response_payload.get('statusCode', 500) != 200:
                    raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
                
                successful_steps += 1
                status_messages.append(f"        - ✅ Added entity: {test_entity} (add_entities)")
                
                # List entities
                event = {
                    'action': 'list',
                    'parent_entity': parent_entity
                }
                
                event_json = json.dumps(event).encode('utf-8')
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=event_json
                )
                
                response_payload = json.loads(response['Payload'].read())
                entities_list = json.loads(response_payload.get('body', '{}')).get('entities', [])
                status_messages.append(f"        - ✅ Listing: {entities_list} (list_entities)")
                successful_steps += 1

                # Check completion status
                event = {
                    'action': 'checkCompleted',
                    'parent_entity': parent_entity
                }
                
                event_json = json.dumps(event).encode('utf-8')
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=event_json
                )
                
                response_payload = json.loads(response['Payload'].read())
                
                if response.get('FunctionError'):
                    raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                    
                if response_payload.get('statusCode', 500) != 200:
                    raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")

                completion_status = json.loads(response_payload.get('body', '{}')).get('all_completed', True)
                if completion_status:
                    raise Exception("Expected completion status to be False")
                
                successful_steps += 1
                status_messages.append("        - ✅ Verified completion status is False (check_completed)")

                # Delete the entity
                event = {
                    'action': 'delete',
                    'parent_entity': parent_entity,
                    'entities': [test_entity]
                }
                
                event_json = json.dumps(event).encode('utf-8')
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=event_json
                )
                
                response_payload = json.loads(response['Payload'].read())
                
                if response.get('FunctionError'):
                    raise Exception(f"Lambda execution failed: {json.dumps(response_payload)}")
                    
                if response_payload.get('statusCode', 500) != 200:
                    raise Exception(f"Lambda returned error: {response_payload.get('body', 'Unknown error')}")
                
                status_messages.append(f"        - ✅ Deleted entity: {test_entity} (delete_entities)")
                successful_steps += 1

                # Get email list
                event = {
                    'action': 'get_email_list',
                    'parent_entity': parent_entity
                }
                
                event_json = json.dumps(event).encode('utf-8')
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=event_json
                )
                
                response_payload = json.loads(response['Payload'].read())
                email_list = json.loads(response_payload.get('body', '{}')).get('email_list', [])
                
                if test_email not in email_list:
                    raise Exception(f"Email {test_email} not found in email list")
                
                successful_steps += 1
                status_messages.append(f"        - ✅ Retrieved email list: {email_list} (get_email_list)")

            except Exception as e:
                status_messages.append(f"        - ❌ Failed to add {test_entity}")
                print(f"❌ handleTable.py failed ({successful_steps}/6)")
                if detailed:
                    for msg in status_messages:
                        print(msg)
                raise
        else:
            status_messages.append("        - ❌ Table setup failed")
            print(f"❌ handleTable.py failed ({successful_steps}/6)")
            if detailed:
                for msg in status_messages:
                    print(msg)
            raise

    # Print final success status if all tests passed
    print(f"✅ handleTable.py successful ({successful_steps}/{total_steps})")
    if detailed:
        for msg in status_messages:
            print(msg)

if __name__ == "__main__":
    test_handleTable(detailed=True)  # Uses default test email 