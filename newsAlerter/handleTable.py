import boto3
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    dynamodb = boto3.client('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    
    # Define table name
    table_name = f"{parent_entity}_TrackedEntities"
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName=table_name)
            raise Exception(f"Table {table_name} already exists. Use a different parent entity name.")
        except dynamodb.exceptions.ResourceNotFoundException:
            # Table doesn't exist, proceed with creation
            pass
        
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
        dynamodb_resource = boto3.resource('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
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
    dynamodb = boto3.client('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    
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
    dynamodb = boto3.client('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    
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

def list_entities(parent_entity: str):
    """
    List all entities in the tracking table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        
    Returns:
        dict: Results of the operation including list of all entity names
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    # Initialize DynamoDB client and resource
    dynamodb = boto3.client('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
    
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
        
        # Scan the table to get all entities
        response = table.scan(
            ProjectionExpression="entity_name"  # Only retrieve the entity_name field
        )
        
        # Extract entity names from response
        entities = [item['entity_name'] for item in response['Items']]
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression="entity_name",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            entities.extend([item['entity_name'] for item in response['Items']])
        
        # Sort entities alphabetically
        entities.sort()
        
        return {
            "message": f"Retrieved {len(entities)} entities from {table_name}",
            "table_name": table_name,
            "entities": entities,
            "count": len(entities)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda handler for managing DynamoDB table operations
    
    Expected event format:
    {
        "action": "setup|add|delete|list",
        "parent_entity": "Stanford",
        "entities": ["Entity1", "Entity2"]  # Required for add/delete actions
    }
    """
    try:
        # Get action and parent_entity from event
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
        if action == "setup":
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
            response = list_entities(parent_entity)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Invalid action: {action}. Must be one of: setup, add, delete, list'
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