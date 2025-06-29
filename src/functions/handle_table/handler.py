import boto3
import os
import json

from shared.utils import load_credentials
from shared.database import (
    create_tracked_entities_table,
    add_entities_to_table,
    delete_entities_from_table,
    list_entities_from_table,
    setup_email_list_table,
    get_email_list as shared_get_email_list,
    update_entity_analysis
)

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
    try:
        # Create table
        response = create_tracked_entities_table(parent_entity)
        
        print(f"✅ Table {parent_entity}_TrackedEntities created successfully!")
        
        return {
            "message": f"Table {parent_entity}_TrackedEntities created successfully",
            "table_name": f"{parent_entity}_TrackedEntities",
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

def add_entities(parent_entity: str, entities: list, analysis: dict = None, completed: bool = False):
    """
    Add new entities to the tracking table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        entities (list): List of entity names to add
        analysis (dict, optional): Analysis data to store with entity. Defaults to empty dict.
        completed (bool, optional): Completion status flag. Defaults to False.
        
    Returns:
        dict: Results of the operation
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    try:
        # Add entities to table
        result = add_entities_to_table(parent_entity, entities, analysis, completed)
        
        # Prepare response
        response = {
            "message": f"Added {len(result['added_entities'])} entities to {parent_entity}_TrackedEntities",
            "table_name": f"{parent_entity}_TrackedEntities",
            "added_entities": result['added_entities']
        }
        
        # Include failures in response if any occurred
        if result['failed_entities']:
            response["failed_entities"] = result['failed_entities']
            
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
    try:
        # Delete entities from table
        result = delete_entities_from_table(parent_entity, entities)
        
        # Prepare response
        response = {
            "message": f"Deleted {len(result['deleted_entities'])} entities from {parent_entity}_TrackedEntities",
            "table_name": f"{parent_entity}_TrackedEntities",
            "deleted_entities": result['deleted_entities']
        }
        
        # Include not found entities in response if any occurred
        if result['not_found_entities']:
            response["not_found_entities"] = result['not_found_entities']
            
        return response
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def list_entities(parent_entity: str, include_analysis: bool = False):
    """
    List all entities in the tracking table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        include_analysis (bool, optional): Whether to include analysis data. Defaults to False.
        
    Returns:
        dict: List of entities with their status
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    try:
        # List entities from table
        entities = list_entities_from_table(parent_entity, include_analysis)
        
        return {
            "message": f"Found {len(entities)} entities in {parent_entity}_TrackedEntities",
            "table_name": f"{parent_entity}_TrackedEntities",
            "entities": entities,
            "total_count": len(entities)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def clear_attributes(parent_entity: str):
    """
    Clear analysis and completion status for all entities in the table.
    This is useful for re-processing all entities.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        
    Returns:
        dict: Results of the operation
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    try:
        # Get all entities
        entities = list_entities_from_table(parent_entity)
        
        if not entities:
            return {
                "message": f"No entities found in {parent_entity}_TrackedEntities",
                "table_name": f"{parent_entity}_TrackedEntities",
                "cleared_count": 0
            }
        
        # Clear analysis for each entity
        cleared_count = 0
        for entity in entities:
            try:
                update_entity_analysis(parent_entity, entity['entity_name'], {}, completed=False)
                cleared_count += 1
            except Exception as e:
                print(f"Failed to clear entity {entity['entity_name']}: {str(e)}")
        
        return {
            "message": f"Cleared analysis for {cleared_count} entities in {parent_entity}_TrackedEntities",
            "table_name": f"{parent_entity}_TrackedEntities",
            "cleared_count": cleared_count,
            "total_entities": len(entities)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def check_completed(parent_entity: str):
    """
    Check completion status of all entities in the table.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        
    Returns:
        dict: Completion status information
        
    Raises:
        Exception: If table doesn't exist or other errors occur
    """
    try:
        # Get all entities
        entities = list_entities_from_table(parent_entity)
        
        if not entities:
            return {
                "message": f"No entities found in {parent_entity}_TrackedEntities",
                "table_name": f"{parent_entity}_TrackedEntities",
                "all_completed": True,
                "completed_entities": 0,
                "total_entities": 0
            }
        
        # Count completed entities
        completed_count = sum(1 for entity in entities if entity.get('completed', False))
        total_count = len(entities)
        
        return {
            "message": f"Completion status for {parent_entity}_TrackedEntities",
            "table_name": f"{parent_entity}_TrackedEntities",
            "all_completed": completed_count == total_count,
            "completed_entities": completed_count,
            "total_entities": total_count,
            "completion_percentage": (completed_count / total_count * 100) if total_count > 0 else 0
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def setup_email_list(parent_entity: str, initial_emails: list):
    """
    Setup email list for a parent entity.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        initial_emails (list): List of email addresses to add
        
    Returns:
        dict: Results of the operation
        
    Raises:
        Exception: If operation fails
    """
    try:
        # Setup email list
        success = setup_email_list_table(parent_entity, initial_emails)
        
        if success:
            return {
                "message": f"Email list setup successfully for {parent_entity}",
                "parent_entity": parent_entity,
                "email_count": len(initial_emails),
                "emails": initial_emails
            }
        else:
            raise Exception("Failed to setup email list")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def get_email_list(parent_entity: str, default_email: str = None) -> list:
    """
    Get email list for a parent entity.
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        default_email (str, optional): Default email to return if no list found
        
    Returns:
        dict: Email list information
        
    Raises:
        Exception: If operation fails
    """
    try:
        # Get email list
        emails = shared_get_email_list(parent_entity, default_email)
        
        return {
            "message": f"Email list retrieved for {parent_entity}",
            "parent_entity": parent_entity,
            "email_count": len(emails),
            "email_list": emails
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def lambda_handler(event, context):
    """Lambda handler for table operations"""
    try:
        # Extract action and parameters from event
        action = event.get('action')
        
        if not action:
            raise Exception("'action' parameter is required")
        
        # Route to appropriate function based on action
        if action == 'setup':
            parent_entity = event.get('parent_entity')
            if not parent_entity:
                raise Exception("'parent_entity' is required for setup action")
            result = setup(parent_entity)
            
        elif action == 'add':
            parent_entity = event.get('parent_entity')
            entities = event.get('entities', [])
            if not parent_entity or not entities:
                raise Exception("'parent_entity' and 'entities' are required for add action")
            result = add_entities(parent_entity, entities)
            
        elif action == 'delete':
            parent_entity = event.get('parent_entity')
            entities = event.get('entities', [])
            if not parent_entity or not entities:
                raise Exception("'parent_entity' and 'entities' are required for delete action")
            result = delete_entities(parent_entity, entities)
            
        elif action == 'list':
            parent_entity = event.get('parent_entity')
            include_analysis = event.get('include_analysis', False)
            if not parent_entity:
                raise Exception("'parent_entity' is required for list action")
            result = list_entities(parent_entity, include_analysis)
            
        elif action == 'clear':
            parent_entity = event.get('parent_entity')
            if not parent_entity:
                raise Exception("'parent_entity' is required for clear action")
            result = clear_attributes(parent_entity)
            
        elif action == 'checkCompleted':
            parent_entity = event.get('parent_entity')
            if not parent_entity:
                raise Exception("'parent_entity' is required for checkCompleted action")
            result = check_completed(parent_entity)
            
        elif action == 'setup_email_list':
            parent_entity = event.get('parent_entity')
            initial_emails = event.get('initial_emails', [])
            if not parent_entity:
                raise Exception("'parent_entity' is required for setup_email_list action")
            result = setup_email_list(parent_entity, initial_emails)
            
        elif action == 'get_email_list':
            parent_entity = event.get('parent_entity')
            default_email = event.get('default_email')
            if not parent_entity:
                raise Exception("'parent_entity' is required for get_email_list action")
            result = get_email_list(parent_entity, default_email)
            
        elif action == 'update':
            parent_entity = event.get('parent_entity')
            entity_name = event.get('entity_name')
            analysis = event.get('analysis', {})
            completed = event.get('completed', False)
            if not parent_entity or not entity_name:
                raise Exception("'parent_entity' and 'entity_name' are required for update action")
            update_entity_analysis(parent_entity, entity_name, analysis, completed)
            result = {
                'message': f"Entity {entity_name} updated successfully in {parent_entity}_TrackedEntities",
                'entity_name': entity_name,
                'parent_entity': parent_entity,
                'analysis': analysis,
                'completed': completed
            }
            
        else:
            raise Exception(f"Unknown action: {action}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        error_message = f"Error in handle_table lambda_handler: {str(e)}"
        print(f"❌ {error_message}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        } 