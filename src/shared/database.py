import boto3
from .utils import load_credentials

def get_dynamodb_client():
    """Get DynamoDB client with credentials"""
    credentials = load_credentials()
    return boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))

def get_dynamodb_resource():
    """Get DynamoDB resource with credentials"""
    credentials = load_credentials()
    return boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))

def get_lambda_client():
    """Get Lambda client with credentials"""
    credentials = load_credentials()
    return boto3.client('lambda', region_name=credentials.get('REGION', 'us-west-1'))

def get_table(table_name: str):
    """Get DynamoDB table resource"""
    dynamodb_resource = get_dynamodb_resource()
    return dynamodb_resource.Table(table_name)

def table_exists(table_name: str) -> bool:
    """Check if DynamoDB table exists"""
    try:
        dynamodb_client = get_dynamodb_client()
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        return False

def create_tracked_entities_table(parent_entity: str):
    """Create DynamoDB table for tracking entities"""
    dynamodb_client = get_dynamodb_client()
    table_name = f"{parent_entity}_TrackedEntities"
    
    # Check if table exists
    if table_exists(table_name):
        raise Exception(f"Table {table_name} already exists")
    
    # Create table
    response = dynamodb_client.create_table(
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
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Wait for table to be created
    dynamodb_client.get_waiter('table_exists').wait(TableName=table_name)
    
    return response

def add_entities_to_table(parent_entity: str, entities: list, analysis: dict = None, completed: bool = False):
    """Add entities to tracking table"""
    if analysis is None:
        analysis = {}
    
    table_name = f"{parent_entity}_TrackedEntities"
    table = get_table(table_name)
    
    added_entities = []
    failed_entities = []
    
    for entity in entities:
        try:
            table.put_item(
                Item={
                    'entity_name': entity,
                    'analysis': analysis,
                    'completed': completed
                }
            )
            added_entities.append(entity)
        except Exception as e:
            print(f"Failed to add entity {entity}: {str(e)}")
            failed_entities.append({
                "entity": entity,
                "error": str(e)
            })
    
    return {
        "added_entities": added_entities,
        "failed_entities": failed_entities
    }

def delete_entities_from_table(parent_entity: str, entities: list):
    """Delete entities from tracking table"""
    table_name = f"{parent_entity}_TrackedEntities"
    table = get_table(table_name)
    
    deleted_entities = []
    not_found_entities = []
    
    for entity in entities:
        try:
            response = table.delete_item(
                Key={'entity_name': entity},
                ReturnValues='ALL_OLD'
            )
            if 'Attributes' in response:
                deleted_entities.append(entity)
            else:
                not_found_entities.append(entity)
        except Exception as e:
            print(f"Failed to delete entity {entity}: {str(e)}")
            not_found_entities.append(entity)
    
    return {
        "deleted_entities": deleted_entities,
        "not_found_entities": not_found_entities
    }

def list_entities_from_table(parent_entity: str, include_analysis: bool = False):
    """List entities from tracking table"""
    table_name = f"{parent_entity}_TrackedEntities"
    table = get_table(table_name)
    
    entities = []
    response = table.scan()
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    for item in items:
        entity_info = {
            'entity_name': item['entity_name'],
            'completed': item.get('completed', False)
        }
        if include_analysis:
            entity_info['analysis'] = item.get('analysis', {})
        entities.append(entity_info)
    
    return entities

def update_entity_analysis(parent_entity: str, entity_name: str, analysis: dict, completed: bool = True):
    """Update entity analysis in tracking table"""
    table_name = f"{parent_entity}_TrackedEntities"
    table = get_table(table_name)
    
    table.update_item(
        Key={'entity_name': entity_name},
        UpdateExpression="SET analysis = :analysis, completed = :completed",
        ExpressionAttributeValues={
            ':analysis': analysis,
            ':completed': completed
        }
    )

def get_email_list_table():
    """Get email list table"""
    return get_table('EmailList')

def setup_email_list_table(parent_entity: str, initial_emails: list):
    """Setup email list for parent entity"""
    table = get_email_list_table()
    
    try:
        table.put_item(
            Item={
                'parent_entity': parent_entity,
                'email_list': initial_emails
            }
        )
        return True
    except Exception as e:
        print(f"Error setting up email list: {str(e)}")
        return False

def get_email_list(parent_entity: str, default_email: str = None) -> list:
    """Get email list for parent entity"""
    table = get_email_list_table()
    
    try:
        response = table.get_item(Key={'parent_entity': parent_entity})
        if 'Item' in response:
            return response['Item']['email_list']
        elif default_email:
            return [default_email]
        else:
            return []
    except Exception as e:
        print(f"Error getting email list: {str(e)}")
        return [default_email] if default_email else [] 