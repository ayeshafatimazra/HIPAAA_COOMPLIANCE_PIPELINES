"""
AWS Lambda function for processing S3 events and updating Glue data catalog.

This function is triggered when new files are uploaded to the S3 data lake
and updates the AWS Glue Data Catalog with metadata and lineage information.
"""

import json
import logging
import boto3
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
glue_client = boto3.client('glue')
s3_client = boto3.client('s3')
rds_client = boto3.client('rds-data')

# Environment variables
GLUE_DATABASE_NAME = os.environ.get('GLUE_DATABASE_NAME', 'hipaa_catalog')
GLUE_TABLE_NAME = os.environ.get('GLUE_TABLE_NAME', 'processed_data')
DATABASE_SECRET_ARN = os.environ.get('DATABASE_SECRET_ARN')
DATABASE_CLUSTER_ARN = os.environ.get('DATABASE_CLUSTER_ARN')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function.
    
    Args:
        event: S3 event notification
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        logger.info(f"Processing S3 event: {json.dumps(event)}")
        
        # Extract S3 event details
        s3_event = event['Records'][0]['s3']
        bucket_name = s3_event['bucket']['name']
        object_key = s3_event['object']['key']
        
        logger.info(f"Processing file: s3://{bucket_name}/{object_key}")
        
        # Extract metadata from the file
        metadata = extract_file_metadata(bucket_name, object_key)
        
        # Update Glue Data Catalog
        update_glue_catalog(bucket_name, object_key, metadata)
        
        # Log lineage information
        log_data_lineage(bucket_name, object_key, metadata)
        
        # Update database with processing status
        update_processing_status(object_key, 'completed', metadata)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'File processed successfully',
                'bucket': bucket_name,
                'key': object_key,
                'metadata': metadata
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing S3 event: {str(e)}")
        
        # Update database with error status
        if 'object_key' in locals():
            update_processing_status(object_key, 'failed', {'error': str(e)})
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process file',
                'message': str(e)
            })
        }


def extract_file_metadata(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Extract metadata from S3 object.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dictionary containing file metadata
    """
    try:
        # Get object metadata
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        
        metadata = {
            'file_size': response['ContentLength'],
            'last_modified': response['LastModified'].isoformat(),
            'content_type': response.get('ContentType', 'application/octet-stream'),
            'encryption': response.get('ServerSideEncryption', 'none'),
            'file_extension': object_key.split('.')[-1] if '.' in object_key else 'unknown',
            'processing_timestamp': datetime.utcnow().isoformat(),
        }
        
        # Extract additional metadata based on file type
        if object_key.endswith('.csv'):
            metadata.update(extract_csv_metadata(bucket_name, object_key))
        elif object_key.endswith('.json'):
            metadata.update(extract_json_metadata(bucket_name, object_key))
        
        logger.info(f"Extracted metadata: {metadata}")
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {'error': str(e)}


def extract_csv_metadata(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Extract metadata from CSV file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dictionary containing CSV metadata
    """
    try:
        # Download first few lines to analyze structure
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read(8192).decode('utf-8')
        lines = content.split('\n')
        
        if len(lines) > 1:
            headers = lines[0].split(',')
            metadata = {
                'file_type': 'csv',
                'column_count': len(headers),
                'columns': headers,
                'sample_data': lines[1:3] if len(lines) > 3 else lines[1:]
            }
        else:
            metadata = {
                'file_type': 'csv',
                'column_count': 0,
                'columns': [],
                'sample_data': []
            }
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting CSV metadata: {str(e)}")
        return {'file_type': 'csv', 'error': str(e)}


def extract_json_metadata(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Extract metadata from JSON file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dictionary containing JSON metadata
    """
    try:
        # Download first part of JSON file
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read(8192).decode('utf-8')
        
        # Try to parse as JSON
        data = json.loads(content)
        
        if isinstance(data, list) and len(data) > 0:
            metadata = {
                'file_type': 'json',
                'data_type': 'array',
                'record_count_estimate': len(data),
                'sample_keys': list(data[0].keys()) if data else []
            }
        elif isinstance(data, dict):
            metadata = {
                'file_type': 'json',
                'data_type': 'object',
                'keys': list(data.keys())
            }
        else:
            metadata = {
                'file_type': 'json',
                'data_type': 'unknown'
            }
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting JSON metadata: {str(e)}")
        return {'file_type': 'json', 'error': str(e)}


def update_glue_catalog(bucket_name: str, object_key: str, metadata: Dict[str, Any]) -> None:
    """
    Update AWS Glue Data Catalog with file metadata.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        metadata: File metadata
    """
    try:
        # Create or update table in Glue Data Catalog
        table_name = f"{GLUE_TABLE_NAME}_{datetime.now().strftime('%Y%m%d')}"
        
        # Define table structure based on file type
        if metadata.get('file_type') == 'csv' and 'columns' in metadata:
            columns = [
                {
                    'Name': col.strip(),
                    'Type': 'string'  # Default to string for safety
                }
                for col in metadata['columns']
            ]
        else:
            columns = [
                {
                    'Name': 'data',
                    'Type': 'string'
                }
            ]
        
        table_input = {
            'Name': table_name,
            'DatabaseName': GLUE_DATABASE_NAME,
            'Description': f'Processed data from {object_key}',
            'TableType': 'EXTERNAL_TABLE',
            'Parameters': {
                'EXTERNAL': 'TRUE',
                'classification': 'csv' if metadata.get('file_type') == 'csv' else 'json'
            },
            'StorageDescriptor': {
                'Columns': columns,
                'Location': f's3://{bucket_name}/{object_key}',
                'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                'SerdeInfo': {
                    'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                    'Parameters': {
                        'field.delim': ',' if metadata.get('file_type') == 'csv' else '\t'
                    }
                }
            }
        }
        
        # Try to create table, update if exists
        try:
            glue_client.create_table(
                DatabaseName=GLUE_DATABASE_NAME,
                TableInput=table_input
            )
            logger.info(f"Created Glue table: {table_name}")
        except glue_client.exceptions.AlreadyExistsException:
            glue_client.update_table(
                DatabaseName=GLUE_DATABASE_NAME,
                TableInput=table_input
            )
            logger.info(f"Updated Glue table: {table_name}")
            
    except Exception as e:
        logger.error(f"Error updating Glue catalog: {str(e)}")


def log_data_lineage(bucket_name: str, object_key: str, metadata: Dict[str, Any]) -> None:
    """
    Log data lineage information for audit purposes.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        metadata: File metadata
    """
    try:
        lineage_info = {
            'source_bucket': bucket_name,
            'source_key': object_key,
            'processing_timestamp': datetime.utcnow().isoformat(),
            'file_metadata': metadata,
            'processing_stage': 's3_event_processing',
            'lambda_function': 's3-processor'
        }
        
        # Store lineage in S3
        lineage_key = f"lineage/{datetime.now().strftime('%Y/%m/%d')}/{object_key.replace('/', '_')}_lineage.json"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=lineage_key,
            Body=json.dumps(lineage_info, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Logged data lineage: {lineage_key}")
        
    except Exception as e:
        logger.error(f"Error logging data lineage: {str(e)}")


def update_processing_status(object_key: str, status: str, metadata: Dict[str, Any]) -> None:
    """
    Update processing status in database.
    
    Args:
        object_key: S3 object key
        status: Processing status
        metadata: Processing metadata
    """
    try:
        if not DATABASE_SECRET_ARN or not DATABASE_CLUSTER_ARN:
            logger.warning("Database credentials not configured, skipping status update")
            return
        
        # SQL to insert/update processing status
        sql = """
        INSERT INTO file_processing_status (
            file_key, processing_status, metadata, updated_at
        ) VALUES (
            :file_key, :status, :metadata, NOW()
        )
        ON CONFLICT (file_key) 
        DO UPDATE SET 
            processing_status = :status,
            metadata = :metadata,
            updated_at = NOW()
        """
        
        parameters = [
            {'name': 'file_key', 'value': {'stringValue': object_key}},
            {'name': 'status', 'value': {'stringValue': status}},
            {'name': 'metadata', 'value': {'stringValue': json.dumps(metadata)}}
        ]
        
        rds_client.execute_statement(
            resourceArn=DATABASE_CLUSTER_ARN,
            secretArn=DATABASE_SECRET_ARN,
            database='hipaa_etl',
            sql=sql,
            parameters=parameters
        )
        
        logger.info(f"Updated processing status for {object_key}: {status}")
        
    except Exception as e:
        logger.error(f"Error updating processing status: {str(e)}") 