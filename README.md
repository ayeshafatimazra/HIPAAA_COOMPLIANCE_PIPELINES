# HIPAA-Compliant ETL Pipeline

A secure, automated ETL pipeline for processing sensitive patient health information (PHI) in compliance with HIPAA regulations.

## Architecture Overview

This pipeline automates the extraction, transformation, and loading of PHI data with end-to-end encryption, audit logging, and comprehensive monitoring.

### Key Components

- **Apache Airflow**: Orchestrates ETL workflows with secure connections
- **AWS S3**: Encrypted data lake with SSE-KMS encryption
- **AWS RDS**: Encrypted relational database for processed data
- **AWS Lambda**: Event-driven transformations and metadata management
- **AWS Glue**: Data catalog and lineage tracking
- **AWS KMS**: Key management for encryption/decryption
- **CloudTrail**: Comprehensive audit logging

## Security Features

- **Encryption at Rest**: All data encrypted with AWS KMS
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Access Controls**: IAM roles with least-privilege policies
- **Audit Logging**: Complete activity tracking via CloudTrail
- **PII Masking**: Automated sensitive data transformation
- **Schema Validation**: Data integrity checks at every stage

## Project Structure

```
├── infrastructure/          # AWS CDK infrastructure code
├── airflow/                 # Airflow DAGs and operators
├── lambda/                  # AWS Lambda functions
├── monitoring/              # Prometheus/Grafana setup
├── ui/                      # React monitoring dashboard
├── scripts/                 # Utility scripts
└── docs/                    # Documentation
```

## Quick Start

1. **Prerequisites**
   - AWS CLI configured
   - Node.js 18+ and AWS CDK
   - Python 3.9+ with required packages
   - Docker (for local development)

2. **Deploy Infrastructure**
   ```bash
   cd infrastructure
   npm install
   cdk deploy --all
   ```

3. **Setup Airflow**
   ```bash
   cd airflow
   pip install -r requirements.txt
   # Configure connections and deploy DAGs
   ```

4. **Start Monitoring**
   ```bash
   cd monitoring
   docker-compose up -d
   ```

## Compliance Features

- ✅ HIPAA-compliant encryption standards
- ✅ End-to-end audit trails
- ✅ Automated PII masking
- ✅ Schema validation and data quality checks
- ✅ Secure access controls
- ✅ Real-time monitoring and alerting

## Contributing

Please ensure all changes maintain HIPAA compliance standards and include appropriate testing.

## License

This project is licensed under the MIT License - see the LICENSE file for details.