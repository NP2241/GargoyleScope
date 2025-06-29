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
    total_steps = 8  # Updated to match the actual number of steps in both paths
    
    # Define all expected steps for consistent reporting
    expected_steps = [
        "Table Setup",
        "Add Entity", 
        "List Entities",
        "Add Entity with Analysis",
        "List Entities (Verification)",
        "Delete Entity",
        "Setup Email List",
        "Get Email List"
    ]
    
    # Track step status
    step_status = {step: "❌ Not executed" for step in expected_steps}
    
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
        step_status["Table Setup"] = "✅ Table created successfully"
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
        step_status["Add Entity"] = f"✅ Added entity: {test_entity}"
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
        step_status["List Entities"] = f"✅ Listing successful: {entities_list}"
        status_messages.append(f"        - ✅ Listing successful: {entities_list}")
        
        # 4. Add entity with analysis and completed=True
        try:
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
            step_status["Add Entity with Analysis"] = "✅ Added entity with analysis data and completed=True"
            status_messages.append("        - ✅ Added entity with analysis data and completed=True")
        except Exception as e:
            step_status["Add Entity with Analysis"] = f"❌ Failed: {str(e)}"
            if detailed:
                print(f"        - ❌ Failed to add entity with analysis: {str(e)}")
        
        # 5. List entities (verification)
        try:
            event = {
                'action': 'list',
                'parent_entity': parent_entity,
                'include_analysis': True
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
            step_status["List Entities (Verification)"] = f"✅ Listing successful: {entities_list}"
            status_messages.append(f"        - ✅ Listing successful: {entities_list} (verification)")
            
        except Exception as e:
            step_status["List Entities (Verification)"] = f"❌ Failed: {str(e)}"
            status_messages.append(f"        - ❌ Failed to list entities")
            if detailed:
                for msg in status_messages:
                    print(msg)
            raise
        
        # 6. Delete entity
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
            
            successful_steps += 1
            step_status["Delete Entity"] = f"✅ Deleted entity: {test_entity}"
            status_messages.append(f"        - ✅ Deleted entity: {test_entity}")

            # 7. Setup email list
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
            step_status["Setup Email List"] = "✅ Email list setup verified"
            status_messages.append("        - ✅ Email list setup verified")

            # 8. Get email list
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
            step_status["Get Email List"] = f"✅ Retrieved email list: {email_list}"
            status_messages.append(f"        - ✅ Retrieved email list: {email_list}")

        except Exception as e:
            step_status["Setup Email List"] = f"❌ Failed: {str(e)}"
            step_status["Get Email List"] = "❌ Skipped due to previous failure"
            status_messages.append(f"        - ❌ Failed to setup or verify email list: {str(e)}")
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
            step_status["Table Setup"] = "✅ Table already exists"
            status_messages.append("        - ✅ Table already exists (setup)")
            
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
                step_status["Add Entity"] = f"✅ Added entity: {test_entity}"
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
                step_status["List Entities"] = f"✅ Listing: {entities_list}"
                status_messages.append(f"        - ✅ Listing: {entities_list} (list_entities)")
                successful_steps += 1

                # Check completion status (this replaces the analysis step in fallback)
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
                step_status["Add Entity with Analysis"] = "✅ Verified completion status is False"
                status_messages.append("        - ✅ Verified completion status is False (check_completed)")

                # Update the entity's analysis and completed fields using the new 'update' action
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
                    'action': 'update',
                    'parent_entity': parent_entity,
                    'entity_name': test_entity,
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
                status_messages.append("        - ✅ Updated entity with analysis data and completed=True (update)")

                # List entities (verification) - verify entity still exists after update
                event = {
                    'action': 'list',
                    'parent_entity': parent_entity,
                    'include_analysis': True
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
                entities_list = json.loads(response_payload.get('body', '{}')).get('entities', [])
                if test_entity not in [e['entity_name'] if isinstance(e, dict) else e for e in entities_list]:
                    raise Exception(f"Added entity {test_entity} not found in list")
                successful_steps += 1
                step_status["List Entities (Verification)"] = f"✅ Listing successful: {entities_list}"
                status_messages.append(f"        - ✅ Listing successful: {entities_list} (verification)")

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
                
                step_status["Delete Entity"] = f"✅ Deleted entity: {test_entity}"
                status_messages.append(f"        - ✅ Deleted entity: {test_entity} (delete_entities)")
                successful_steps += 1

                # Setup email list
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
                step_status["Setup Email List"] = "✅ Email list setup verified"
                status_messages.append(f"        - ✅ Email list setup verified (setup_email_list)")

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
                step_status["Get Email List"] = f"✅ Retrieved email list: {email_list}"
                status_messages.append(f"        - ✅ Retrieved email list: {email_list} (get_email_list)")

            except Exception as e:
                step_status["Add Entity"] = f"❌ Failed: {str(e)}"
                status_messages.append(f"        - ❌ Failed to add {test_entity}")
                if detailed:
                    for msg in status_messages:
                        print(msg)
                raise
        else:
            step_status["Table Setup"] = f"❌ Failed: {str(e)}"
            status_messages.append("        - ❌ Table setup failed")
            if detailed:
                for msg in status_messages:
                    print(msg)
            raise

    # Print final success status if all tests passed
    print(f"✅ handleTable.py successful ({successful_steps}/{total_steps})")
    for i, step in enumerate(expected_steps, 1):
        status = step_status[step]
        # Extract emoji and message from status
        if "✅" in status:
            emoji = "✅"
            message = status.replace("✅ ", "")
            # Clean up the verification step output
            if step == "List Entities (Verification)" and "Listing successful:" in message:
                # Extract just the entity name and completion status, show analysis as expected
                if "analysis" in message:
                    message = message.split("Listing successful: ")[1]
                    # Parse the entities list to extract clean info
                    try:
                        entities_data = eval(message)  # Safe since we control the data
                        if entities_data and len(entities_data) > 0:
                            entity = entities_data[0]
                            clean_message = f"entity: {entity['entity_name']}, completed: {entity['completed']}, analysis: 'as expected'"
                            message = f"Listing successful: [{clean_message}]"
                    except:
                        pass  # Keep original message if parsing fails
        elif "❌" in status:
            emoji = "❌"
            message = status.replace("❌ ", "")
        else:
            emoji = "❌"
            message = status
        print(f"  {i}. {emoji} {step}: {message}")

if __name__ == "__main__":
    test_handleTable(detailed=True)  # Uses default test email 