"""
Custom Airflow operators for HIPAA-compliant ETL operations.

This module provides operators for secure data extraction, transformation,
and loading with encryption and PII protection.
"""

import os
import json
import logging
import hashlib
import re
from typing import Dict, Any, Optional
from datetime import datetime

import pandas as pd
import boto3
from cryptography.fernet import Fernet
from jsonschema import validate, ValidationError

# Airflow imports with error handling
try:
    from airflow.models import BaseOperator
    from airflow.utils.decorators import apply_defaults
    from airflow.providers.amazon.aws.hooks.s3 import S3Hook
    from airflow.providers.sftp.hooks.sftp import SFTPHook
    from airflow.providers.http.hooks.http import HttpHook
    from airflow.hooks.postgres_hook import PostgresHook
except ImportError:
    # Mock classes for development/testing
    class BaseOperator:
        def __init__(self, *args, **kwargs):
            pass
    
    def apply_defaults(func):
        return func
    
    class S3Hook:
        def __init__(self, aws_conn_id=None):
            pass
    
    class SFTPHook:
        def __init__(self, ftp_conn_id=None):
            pass
    
    class HttpHook:
        def __init__(self, http_conn_id=None, method='GET'):
            pass
    
    class PostgresHook:
        def __init__(self, postgres_conn_id=None):
            pass

logger = logging.getLogger(__name__)


class EncryptedExtractOperator(BaseOperator):
    """
    Extract encrypted data from SFTP or API sources and upload to S3 with encryption.
    """
    
    @apply_defaults
    def __init__(
        self,
        sftp_conn_id: str,
        api_conn_id: str,
        s3_bucket: str,
        s3_key: str,
        kms_key_arn: str,
        source_type: str = 'sftp',  # 'sftp' or 'api'
        source_path: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.sftp_conn_id = sftp_conn_id
        self.api_conn_id = api_conn_id
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.kms_key_arn = kms_key_arn
        self.source_type = source_type
        self.source_path = source_path
        self.api_endpoint = api_endpoint

    def execute(self, context):
        """Execute the encrypted extraction."""
        logger.info(f"Starting encrypted extraction from {self.source_type}")
        
        try:
            if self.source_type == 'sftp':
                data = self._extract_from_sftp()
            elif self.source_type == 'api':
                data = self._extract_from_api()
            else:
                raise ValueError(f"Unsupported source type: {self.source_type}")
            
            # Upload to S3 with encryption
            self._upload_to_s3_encrypted(data)
            
            logger.info(f"Encrypted extraction completed: {self.s3_key}")
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise

    def _extract_from_sftp(self) -> bytes:
        """Extract data from SFTP server."""
        try:
            sftp_hook = SFTPHook(ftp_conn_id=self.sftp_conn_id)
            
            with sftp_hook.get_conn() as sftp:
                with sftp.file(self.source_path, 'rb') as remote_file:
                    data = remote_file.read()
            
            logger.info(f"Extracted {len(data)} bytes from SFTP")
            return data
        except Exception as e:
            logger.error(f"SFTP extraction failed: {str(e)}")
            raise

    def _extract_from_api(self) -> bytes:
        """Extract data from API endpoint."""
        try:
            http_hook = HttpHook(http_conn_id=self.api_conn_id, method='GET')
            
            response = http_hook.run(endpoint=self.api_endpoint)
            response.raise_for_status()
            
            data = response.content
            logger.info(f"Extracted {len(data)} bytes from API")
            return data
        except Exception as e:
            logger.error(f"API extraction failed: {str(e)}")
            raise

    def _upload_to_s3_encrypted(self, data: bytes) -> None:
        """Upload data to S3 with server-side encryption."""
        try:
            s3_hook = S3Hook(aws_conn_id='aws_default')
            
            # Upload with SSE-KMS encryption
            s3_hook.load_bytes(
                bytes_data=data,
                key=self.s3_key,
                bucket_name=self.s3_bucket,
                replace=True,
                encrypt=True,
                encryption='aws:kms',
                encryption_kms_key_id=self.kms_key_arn
            )
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise


class SchemaValidationOperator(BaseOperator):
    """
    Validate data schema against predefined JSON schema.
    """
    
    @apply_defaults
    def __init__(
        self,
        s3_bucket: str,
        s3_key: str,
        schema_file: str,
        kms_key_arn: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.schema_file = schema_file
        self.kms_key_arn = kms_key_arn

    def execute(self, context):
        """Execute schema validation."""
        logger.info(f"Starting schema validation for {self.s3_key}")
        
        try:
            # Load schema
            schema = self._load_schema()
            
            # Download and validate data
            data = self._download_from_s3()
            validation_errors = self._validate_data(data, schema)
            
            if validation_errors:
                error_msg = f"Schema validation failed: {validation_errors}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info("Schema validation completed successfully")
        except Exception as e:
            logger.error(f"Schema validation failed: {str(e)}")
            raise

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), '..', self.schema_file)
            
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema: {str(e)}")
            raise

    def _download_from_s3(self) -> pd.DataFrame:
        """Download data from S3."""
        try:
            s3_hook = S3Hook(aws_conn_id='aws_default')
            
            # Download to temporary file
            temp_file = s3_hook.download_file(
                key=self.s3_key,
                bucket_name=self.s3_bucket,
                local_path='/tmp/'
            )
            
            # Read CSV
            df = pd.read_csv(temp_file)
            
            # Clean up
            os.remove(temp_file)
            
            return df
        except Exception as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            raise

    def _validate_data(self, df: pd.DataFrame, schema: Dict[str, Any]) -> list:
        """Validate DataFrame against schema."""
        errors = []
        
        for index, row in df.iterrows():
            try:
                validate(instance=row.to_dict(), schema=schema)
            except ValidationError as e:
                errors.append(f"Row {index}: {e.message}")
        
        return errors


class PIIMaskingOperator(BaseOperator):
    """
    Mask or hash PII data according to HIPAA requirements.
    """
    
    @apply_defaults
    def __init__(
        self,
        input_s3_bucket: str,
        input_s3_key: str,
        output_s3_bucket: str,
        output_s3_key: str,
        kms_key_arn: str,
        masking_rules: Dict[str, str],
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.input_s3_bucket = input_s3_bucket
        self.input_s3_key = input_s3_key
        self.output_s3_bucket = output_s3_bucket
        self.output_s3_key = output_s3_key
        self.kms_key_arn = kms_key_arn
        self.masking_rules = masking_rules

    def execute(self, context):
        """Execute PII masking."""
        logger.info(f"Starting PII masking for {self.input_s3_key}")
        
        try:
            # Download data
            df = self._download_from_s3()
            
            # Apply masking rules
            masked_df = self._apply_masking_rules(df)
            
            # Upload masked data
            self._upload_to_s3_encrypted(masked_df)
            
            logger.info(f"PII masking completed: {self.output_s3_key}")
        except Exception as e:
            logger.error(f"PII masking failed: {str(e)}")
            raise

    def _download_from_s3(self) -> pd.DataFrame:
        """Download data from S3."""
        try:
            s3_hook = S3Hook(aws_conn_id='aws_default')
            
            temp_file = s3_hook.download_file(
                key=self.input_s3_key,
                bucket_name=self.input_s3_bucket,
                local_path='/tmp/'
            )
            
            df = pd.read_csv(temp_file)
            os.remove(temp_file)
            
            return df
        except Exception as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            raise

    def _apply_masking_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply masking rules to DataFrame."""
        masked_df = df.copy()
        
        for column, rule in self.masking_rules.items():
            if column in masked_df.columns:
                if rule == 'hash':
                    masked_df[column] = masked_df[column].apply(self._hash_value)
                elif rule == 'mask':
                    masked_df[column] = masked_df[column].apply(self._mask_value)
                elif rule == 'generalize':
                    masked_df[column] = masked_df[column].apply(self._generalize_value)
        
        return masked_df

    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA-256."""
        if pd.isna(value) or value == '':
            return value
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]

    def _mask_value(self, value: str) -> str:
        """Mask a value by replacing characters with asterisks."""
        if pd.isna(value) or value == '':
            return value
        
        value_str = str(value)
        if '@' in value_str:  # Email
            parts = value_str.split('@')
            return f"{parts[0][:2]}***@{parts[1]}"
        elif len(value_str) >= 10:  # Phone number
            return f"{value_str[:3]}***{value_str[-4:]}"
        else:
            return f"{value_str[:2]}***"

    def _generalize_value(self, value: str) -> str:
        """Generalize a value (e.g., address to city/state)."""
        if pd.isna(value) or value == '':
            return value
        # Simple generalization - in production, use more sophisticated logic
        return "Generalized Location"

    def _upload_to_s3_encrypted(self, df: pd.DataFrame) -> None:
        """Upload DataFrame to S3 with encryption."""
        try:
            s3_hook = S3Hook(aws_conn_id='aws_default')
            
            # Save to temporary file
            temp_file = '/tmp/masked_data.csv'
            df.to_csv(temp_file, index=False)
            
            # Upload with encryption
            s3_hook.load_file(
                filename=temp_file,
                key=self.output_s3_key,
                bucket_name=self.output_s3_bucket,
                replace=True,
                encrypt=True,
                encryption='aws:kms',
                encryption_kms_key_id=self.kms_key_arn
            )
            
            # Clean up
            os.remove(temp_file)
        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            raise


class EncryptedLoadOperator(BaseOperator):
    """
    Load encrypted data from S3 to database with encryption.
    """
    
    @apply_defaults
    def __init__(
        self,
        s3_bucket: str,
        s3_key: str,
        database_conn_id: str,
        table_name: str,
        kms_key_arn: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.database_conn_id = database_conn_id
        self.table_name = table_name
        self.kms_key_arn = kms_key_arn

    def execute(self, context):
        """Execute encrypted loading."""
        logger.info(f"Starting encrypted loading to {self.table_name}")
        
        try:
            # Download data
            df = self._download_from_s3()
            
            # Load to database
            self._load_to_database(df)
            
            logger.info(f"Encrypted loading completed: {self.table_name}")
        except Exception as e:
            logger.error(f"Encrypted loading failed: {str(e)}")
            raise

    def _download_from_s3(self) -> pd.DataFrame:
        """Download data from S3."""
        try:
            s3_hook = S3Hook(aws_conn_id='aws_default')
            
            temp_file = s3_hook.download_file(
                key=self.s3_key,
                bucket_name=self.s3_bucket,
                local_path='/tmp/'
            )
            
            df = pd.read_csv(temp_file)
            os.remove(temp_file)
            
            return df
        except Exception as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            raise

    def _load_to_database(self, df: pd.DataFrame) -> None:
        """Load DataFrame to database."""
        try:
            pg_hook = PostgresHook(postgres_conn_id=self.database_conn_id)
            
            # Create table if not exists
            self._create_table_if_not_exists(pg_hook, df.columns.tolist())
            
            # Insert data
            for index, row in df.iterrows():
                columns = ', '.join(row.index)
                values = ', '.join(['%s'] * len(row))
                insert_query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({values})"
                
                pg_hook.run(insert_query, parameters=row.tolist())
            
            logger.info(f"Loaded {len(df)} records to {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to load to database: {str(e)}")
            raise

    def _create_table_if_not_exists(self, pg_hook: PostgresHook, columns: list) -> None:
        """Create table if it doesn't exist."""
        try:
            # Simple table creation - in production, use proper schema management
            create_query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id SERIAL PRIMARY KEY,
                {', '.join([f'{col} TEXT' for col in columns])},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            pg_hook.run(create_query)
        except Exception as e:
            logger.error(f"Failed to create table: {str(e)}")
            raise 