"""
HIPAA-Compliant ETL Pipeline DAG

This DAG orchestrates the extraction, transformation, and loading of PHI data
with end-to-end encryption and audit logging.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.sftp.hooks.sftp import SFTPHook
from airflow.providers.http.hooks.http import HttpHook
from airflow.models import Variable

from operators.hipaa_operators import (
    EncryptedExtractOperator,
    PIIMaskingOperator,
    SchemaValidationOperator,
    EncryptedLoadOperator
)

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'hipaa-etl-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    'hipaa_etl_pipeline',
    default_args=default_args,
    description='HIPAA-compliant ETL pipeline for PHI data processing',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    max_active_runs=1,
    tags=['hipaa', 'etl', 'phi', 'compliance'],
)

# Configuration
S3_BUCKET = Variable.get('hipaa_s3_bucket')
KMS_KEY_ARN = Variable.get('hipaa_kms_key_arn')
DATABASE_CONN_ID = 'hipaa_postgres'
SFTP_CONN_ID = 'hipaa_sftp'
API_CONN_ID = 'hipaa_api'

# Extract task
extract_task = EncryptedExtractOperator(
    task_id='extract_phi_data',
    sftp_conn_id=SFTP_CONN_ID,
    api_conn_id=API_CONN_ID,
    s3_bucket=S3_BUCKET,
    s3_key='raw/{{ ds }}/phi_data.csv',
    kms_key_arn=KMS_KEY_ARN,
    dag=dag,
)

# Schema validation task
validate_schema_task = SchemaValidationOperator(
    task_id='validate_schema',
    s3_bucket=S3_BUCKET,
    s3_key='raw/{{ ds }}/phi_data.csv',
    schema_file='schemas/phi_schema.json',
    kms_key_arn=KMS_KEY_ARN,
    dag=dag,
)

# PII masking task
mask_pii_task = PIIMaskingOperator(
    task_id='mask_pii_data',
    input_s3_bucket=S3_BUCKET,
    input_s3_key='raw/{{ ds }}/phi_data.csv',
    output_s3_bucket=S3_BUCKET,
    output_s3_key='processed/{{ ds }}/phi_data_cleaned.csv',
    kms_key_arn=KMS_KEY_ARN,
    masking_rules={
        'ssn': 'hash',
        'email': 'mask',
        'phone': 'mask',
        'address': 'generalize'
    },
    dag=dag,
)

# Load to RDS task
load_to_rds_task = EncryptedLoadOperator(
    task_id='load_to_rds',
    s3_bucket=S3_BUCKET,
    s3_key='processed/{{ ds }}/phi_data_cleaned.csv',
    database_conn_id=DATABASE_CONN_ID,
    table_name='phi_data',
    kms_key_arn=KMS_KEY_ARN,
    dag=dag,
)

# Data quality check task
data_quality_check = PythonOperator(
    task_id='data_quality_check',
    python_callable=perform_data_quality_check,
    op_kwargs={
        'database_conn_id': DATABASE_CONN_ID,
        'table_name': 'phi_data',
        'date': '{{ ds }}'
    },
    dag=dag,
)

# Audit logging task
audit_log_task = PythonOperator(
    task_id='audit_log_completion',
    python_callable=log_etl_completion,
    op_kwargs={
        'dag_run_id': '{{ run_id }}',
        'execution_date': '{{ ds }}',
        'status': 'success'
    },
    dag=dag,
)

# Task dependencies
extract_task >> validate_schema_task >> mask_pii_task >> load_to_rds_task >> data_quality_check >> audit_log_task

def perform_data_quality_check(database_conn_id: str, table_name: str, date: str) -> None:
    """
    Perform data quality checks on loaded data.
    
    Args:
        database_conn_id: Airflow connection ID for database
        table_name: Name of the table to check
        date: Date of the data load
    """
    from airflow.hooks.postgres_hook import PostgresHook
    
    pg_hook = PostgresHook(postgres_conn_id=database_conn_id)
    
    # Check for null values in required fields
    null_check_query = f"""
    SELECT COUNT(*) as null_count
    FROM {table_name}
    WHERE load_date = '{date}'
    AND (patient_id IS NULL OR encounter_date IS NULL)
    """
    
    null_count = pg_hook.get_first(null_check_query)[0]
    
    if null_count > 0:
        raise ValueError(f"Found {null_count} records with null required fields")
    
    # Check for duplicate records
    duplicate_check_query = f"""
    SELECT COUNT(*) as duplicate_count
    FROM (
        SELECT patient_id, encounter_date, COUNT(*)
        FROM {table_name}
        WHERE load_date = '{date}'
        GROUP BY patient_id, encounter_date
        HAVING COUNT(*) > 1
    ) duplicates
    """
    
    duplicate_count = pg_hook.get_first(duplicate_check_query)[0]
    
    if duplicate_count > 0:
        raise ValueError(f"Found {duplicate_count} duplicate records")
    
    logger.info(f"Data quality checks passed for {date}")

def log_etl_completion(dag_run_id: str, execution_date: str, status: str) -> None:
    """
    Log ETL completion for audit purposes.
    
    Args:
        dag_run_id: Airflow DAG run ID
        execution_date: Date of execution
        status: Status of the ETL run
    """
    from airflow.hooks.postgres_hook import PostgresHook
    
    pg_hook = PostgresHook(postgres_conn_id=DATABASE_CONN_ID)
    
    audit_query = """
    INSERT INTO etl_audit_log (
        dag_run_id, execution_date, status, completed_at, 
        records_processed, error_message
    ) VALUES (
        %s, %s, %s, NOW(), 
        (SELECT COUNT(*) FROM phi_data WHERE load_date = %s),
        NULL
    )
    """
    
    pg_hook.run(audit_query, parameters=[
        dag_run_id, execution_date, status, execution_date
    ])
    
    logger.info(f"ETL completion logged: {dag_run_id} - {status}") 