import boto3
import os
import json

# Load credentials from env.json
def load_credentials():
    try:
        with open('env.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # In Lambda, use environment variables
        return {
            'REGION': os.environ.get('REGION', 'us-west-1')
        }

def setup(parent_entity: str):
    """
    Create empty DynamoDB table for tracking entities and their analysis status.
    Fails if table already exists.
    
    Table name format: ParentEntity_TrackedEntities (e.g., Stanford_TrackedEntities)
    
    Schema:
        - entity_name (String) - Partition Key
        - analysis (Map) - JSON object for analysis results
        - completed (Boolean) - Processing status flag
    """
    # Initialize DynamoDB client
    credentials = load_credentials()
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    # Check if table exists
    try:
        dynamodb.describe_table(TableName=table_name)
        raise Exception(f"Table {table_name} already exists")
    except dynamodb.exceptions.ResourceNotFoundException:
        # Table doesn't exist, proceed with creation
        pass
        
    try:
        # Create table
        response = dynamodb.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {
                    'AttributeName': 'entity_name',
                    'AttributeType': 'S'
                }
            ],
            KeySchema=[
                {
                    'AttributeName': 'entity_name',
                    'KeyType': 'HASH'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand capacity mode
        )
        
        print(f"Creating table {table_name}...")
        
        # Wait for table to be created
        dynamodb.get_waiter('table_exists').wait(TableName=table_name)
        
        # Verify table structure by adding a test item and then removing it
        dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
        table = dynamodb_resource.Table(table_name)
        
        # Add test item to verify schema
        test_item = {
            'entity_name': '_test_entity',
            'analysis': {},
            'completed': False
        }
        table.put_item(Item=test_item)
        
        # Remove test item
        table.delete_item(Key={'entity_name': '_test_entity'})
        
        print(f"✅ Table {table_name} created successfully with required schema!")
        
        return {
            "message": f"Table {table_name} created successfully",
            "table_name": table_name,
            "schema": {
                "entity_name": "String (Partition Key)",
                "analysis": "Map (JSON)",
                "completed": "Boolean"
            },
            "response": response
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def add_entities(parent_entity: str, entities: list):
    """
    Add new entities to the tracking table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        entities (list): List of entity names to add
        
    Returns:
        dict: Results of the operation
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    # Initialize DynamoDB client and resource
    credentials = load_credentials()
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName=table_name)
        except dynamodb.exceptions.ResourceNotFoundException:
            raise Exception(f"Table {table_name} does not exist. Please create it first using the setup action.")
        
        # Get table resource
        table = dynamodb_resource.Table(table_name)
        
        # Track successful and failed additions
        added_entities = []
        failed_entities = []
        
        # Add each entity
        for entity in entities:
            try:
                table.put_item(
                    Item={
                        'entity_name': entity,
                        'analysis': {},  # Empty JSON object
                        'completed': False
                    }
                )
                added_entities.append(entity)
            except Exception as e:
                print(f"Failed to add entity {entity}: {str(e)}")
                failed_entities.append({
                    "entity": entity,
                    "error": str(e)
                })
        
        # Prepare response
        response = {
            "message": f"Added {len(added_entities)} entities to {table_name}",
            "table_name": table_name,
            "added_entities": added_entities
        }
        
        # Include failures in response if any occurred
        if failed_entities:
            response["failed_entities"] = failed_entities
            
        return response
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def delete_entities(parent_entity: str, entities: list):
    """
    Delete specified entities from the tracking table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        entities (list): List of entity names to delete
        
    Returns:
        dict: Results of the operation including deleted and not found entities
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    # Initialize DynamoDB client and resource
    credentials = load_credentials()
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName=table_name)
        except dynamodb.exceptions.ResourceNotFoundException:
            raise Exception(f"Table {table_name} does not exist. Please create it first using the setup action.")
        
        # Get table resource
        table = dynamodb_resource.Table(table_name)
        
        # Track successful deletions and not found entities
        deleted_entities = []
        not_found_entities = []
        failed_deletions = []
        
        # Delete each entity
        for entity in entities:
            try:
                # Try to get the item first to check if it exists
                response = table.get_item(
                    Key={
                        'entity_name': entity
                    }
                )
                
                if 'Item' in response:
                    # Item exists, delete it
                    table.delete_item(
                        Key={
                            'entity_name': entity
                        }
                    )
                    deleted_entities.append(entity)
                else:
                    # Item doesn't exist
                    not_found_entities.append(entity)
                    
            except Exception as e:
                print(f"Failed to delete entity {entity}: {str(e)}")
                failed_deletions.append({
                    "entity": entity,
                    "error": str(e)
                })
        
        # Prepare response
        response = {
            "message": f"Processed deletion request for {len(entities)} entities from {table_name}",
            "table_name": table_name,
            "deleted_entities": deleted_entities,
            "entities_not_found": not_found_entities
        }
        
        # Include failures in response if any occurred
        if failed_deletions:
            response["failed_deletions"] = failed_deletions
            
        # Add summary counts
        response["summary"] = {
            "total_requested": len(entities),
            "successfully_deleted": len(deleted_entities),
            "not_found": len(not_found_entities),
            "failed": len(failed_deletions)
        }
            
        return response
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def list_entities(parent_entity: str, include_analysis: bool = False):
    """
    List all entities in the tracking table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        include_analysis (bool): Whether to include analysis data in response
        
    Returns:
        dict: Results of the operation including list of all entity names and optionally their analysis
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    # Initialize DynamoDB client and resource
    credentials = load_credentials()
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName=table_name)
        except dynamodb.exceptions.ResourceNotFoundException:
            raise Exception(f"Table {table_name} does not exist. Please create it first using the setup action.")
        
        # Get table resource
        table = dynamodb_resource.Table(table_name)
        
        # Scan the table - include analysis if requested
        projection = "entity_name, analysis" if include_analysis else "entity_name"
        response = table.scan(
            ProjectionExpression=projection
        )
        
        # Extract items from response
        items = response['Items']
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression=projection,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
        
        # Sort items by entity name
        items.sort(key=lambda x: x['entity_name'])
        
        # Prepare response based on include_analysis flag
        if include_analysis:
            result = {
                "message": f"Retrieved {len(items)} entities with analysis from {table_name}",
                "table_name": table_name,
                "entities": items,
                "count": len(items)
            }
        else:
            # Extract just the entity names
            entity_names = [item['entity_name'] for item in items]
            result = {
                "message": f"Retrieved {len(entity_names)} entities from {table_name}",
                "table_name": table_name,
                "entities": entity_names,
                "count": len(entity_names)
            }
        
        return result
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def clear_attributes(parent_entity: str):
    """
    Clear analysis fields and reset completed flags for all entities in the table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        
    Returns:
        dict: Results of the operation including number of entities cleared
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    # Initialize DynamoDB client and resource
    credentials = load_credentials()
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName=table_name)
        except dynamodb.exceptions.ResourceNotFoundException:
            raise Exception(f"Table {table_name} does not exist. Please create it first using the setup action.")
        
        # Get table resource
        table = dynamodb_resource.Table(table_name)
        
        # Get all entities
        response = table.scan(ProjectionExpression="entity_name")
        entities = [item['entity_name'] for item in response['Items']]
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression="entity_name",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            entities.extend([item['entity_name'] for item in response['Items']])
        
        # Track successful and failed updates
        cleared_entities = []
        failed_entities = []
        
        # Update each entity
        for entity in entities:
            try:
                table.update_item(
                    Key={'entity_name': entity},
                    UpdateExpression="SET analysis = :empty_analysis, completed = :false",
                    ExpressionAttributeValues={
                        ':empty_analysis': {},
                        ':false': False
                    }
                )
                cleared_entities.append(entity)
            except Exception as e:
                print(f"Failed to clear attributes for entity {entity}: {str(e)}")
                failed_entities.append({
                    "entity": entity,
                    "error": str(e)
                })
        
        # Prepare response
        response = {
            "message": f"Cleared attributes for {len(cleared_entities)} entities in {table_name}",
            "table_name": table_name,
            "cleared_entities": cleared_entities,
            "summary": {
                "total_entities": len(entities),
                "successfully_cleared": len(cleared_entities),
                "failed": len(failed_entities)
            }
        }
        
        # Include failures in response if any occurred
        if failed_entities:
            response["failed_entities"] = failed_entities
        
        return response
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def check_completed(parent_entity: str):
    """
    Check if all entities in the table have completed=True
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        
    Returns:
        dict: Results of the operation including completion status
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    # Initialize DynamoDB client and resource
    credentials = load_credentials()
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName=table_name)
        except dynamodb.exceptions.ResourceNotFoundException:
            raise Exception(f"Table {table_name} does not exist. Please create it first using the setup action.")
        
        # Get table resource
        table = dynamodb_resource.Table(table_name)
        
        # Scan the table to get all entities and their completed status
        response = table.scan(
            ProjectionExpression="entity_name, completed"
        )
        
        entities = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression="entity_name, completed",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            entities.extend(response['Items'])
        
        # Check if any entities exist
        if not entities:
            return {
                "message": f"No entities found in table {table_name}",
                "table_name": table_name,
                "all_completed": False,
                "total_entities": 0,
                "completed_entities": 0
            }
        
        # Count completed entities
        completed_entities = [e for e in entities if e.get('completed', False) is True]
        
        # All entities must exist and be marked as completed
        all_completed = len(completed_entities) == len(entities)
        
        return {
            "message": f"Checked completion status for {len(entities)} entities in {table_name}",
            "table_name": table_name,
            "all_completed": all_completed,
            "total_entities": len(entities),
            "completed_entities": len(completed_entities)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda handler for managing DynamoDB table operations
    """
    try:
        credentials = load_credentials()
        # Initialize DynamoDB client
        dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
        
        # Regular API actions continue below...
        action = event.get('action')
        parent_entity = event.get('parent_entity')
        
        # Validate required parameters
        if not action or not parent_entity:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'action and parent_entity are required'
                })
            }
        
        # Execute requested action
        if action == "processEmail":
            # Get email details
            email_data = event.get('email', {})
            sender = email_data.get('from')
            content = email_data.get('content')
            
            # Verify sender is authorized
            authorized_emails = [
                "neilpendyala@gmail.com",  # Default from master.py
                credentials.get('REPORT_EMAIL')   # From credentials
            ]
            
            if not sender or sender not in authorized_emails:
                return {
                    'statusCode': 403,
                    'body': json.dumps({
                        'error': 'Unauthorized email sender'
                    })
                }
            
            # Parse commands from email
            commands = parse_email_commands(content)
            
            # Process ADD commands
            add_response = None
            if commands['add']:
                add_response = add_entities(parent_entity, commands['add'])
            
            # Process DELETE commands
            delete_response = None
            if commands['delete']:
                delete_response = delete_entities(parent_entity, commands['delete'])
            
            # Prepare response
            response = {
                'message': 'Email processed successfully',
                'add_results': add_response,
                'delete_results': delete_response
            }
            
            return {
                'statusCode': 200,
                'body': json.dumps(response)
            }
            
        elif action == "setup":
            response = setup(parent_entity)
        elif action == "add":
            entities = event.get('entities', [])
            if not entities:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'entities list is required for add action'
                    })
                }
            response = add_entities(parent_entity, entities)
        elif action == "delete":
            entities = event.get('entities', [])
            if not entities:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'entities list is required for delete action'
                    })
                }
            response = delete_entities(parent_entity, entities)
        elif action == "list":
            include_analysis = event.get('include_analysis', False)
            response = list_entities(parent_entity, include_analysis)
        elif action == "clear":
            response = clear_attributes(parent_entity)
        elif action == "checkCompleted":
            response = check_completed(parent_entity)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Invalid action: {action}. Must be one of: setup, add, delete, list, clear, checkCompleted'
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 