# HIPAA ETL Pipeline - Quick Start Guide

## 🚀 Getting Started

This guide will help you get the HIPAA ETL pipeline up and running quickly.

## Prerequisites

- Python 3.8+
- Node.js 16+
- AWS CLI (for cloud deployment)
- Docker (optional, for monitoring stack)

## 📋 Installation Steps

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd HIPAAA_COOMPLIANCE_PIPELINES

# Install Python dependencies
cd airflow
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-simple.txt

# Install Node.js dependencies
cd ../ui
npm install

# Install AWS CDK dependencies
cd ../infrastructure
npm install
```

### 2. Configure AWS (Optional)

```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Start Local Development

#### Start Airflow
```bash
cd airflow
source venv/bin/activate

# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Start Airflow webserver (in background)
airflow webserver --port 8080 &

# Start Airflow scheduler (in background)
airflow scheduler &
```

#### Start Monitoring Dashboard
```bash
cd ui
npm start
```

The dashboard will be available at: http://localhost:3000

### 4. Access Airflow UI

Open your browser and navigate to: http://localhost:8080

- Username: `admin`
- Password: `admin`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `airflow` directory:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hipaa_etl
DB_USER=postgres
DB_PASSWORD=your_password

# SFTP Configuration
SFTP_HOST=your_sftp_host
SFTP_USERNAME=your_username
SFTP_PASSWORD=your_password

# API Configuration
API_BASE_URL=https://api.example.com
API_KEY=your_api_key
```

### Airflow Connections

Configure Airflow connections through the UI or using the CLI:

```bash
# AWS Connection
airflow connections add 'aws_default' \
    --conn-type 'aws' \
    --conn-login 'your_access_key' \
    --conn-password 'your_secret_key' \
    --conn-extra '{"region_name": "us-east-1"}'

# Database Connection
airflow connections add 'postgres_default' \
    --conn-type 'postgres' \
    --conn-host 'localhost' \
    --conn-login 'postgres' \
    --conn-password 'your_password' \
    --conn-schema 'hipaa_etl'

# SFTP Connection
airflow connections add 'sftp_default' \
    --conn-type 'sftp' \
    --conn-host 'your_sftp_host' \
    --conn-login 'your_username' \
    --conn-password 'your_password'
```

## 🏗️ Deploy to AWS (Optional)

### 1. Deploy Infrastructure

```bash
cd infrastructure

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all
```

### 2. Configure Airflow for AWS

Update the Airflow configuration to use the deployed AWS resources:

```bash
# Update environment variables with AWS resource ARNs
export S3_BUCKET=your-deployed-bucket-name
export RDS_ENDPOINT=your-deployed-rds-endpoint
export GLUE_CATALOG=your-deployed-glue-catalog
```

## 📊 Monitoring

### Local Monitoring

1. **Airflow UI**: http://localhost:8080
2. **React Dashboard**: http://localhost:3000
3. **Grafana** (if Docker is available): http://localhost:3001

### Cloud Monitoring

1. **CloudWatch**: AWS console → CloudWatch
2. **Grafana**: Deployed Grafana instance
3. **Custom Dashboard**: Deployed React application

## 🧪 Testing

### Run Test DAGs

1. Go to Airflow UI: http://localhost:8080
2. Navigate to DAGs
3. Find `hipaa_etl_dag`
4. Click "Trigger DAG" to run manually

### Test Data

Sample test data is included in the `data/` directory:

```bash
# View sample PHI data
cat data/sample_phi_data.json

# View schema definition
cat data/phi_schema.json
```

## 🔒 Security Features

The pipeline includes the following HIPAA-compliant security measures:

- **Encryption at Rest**: All data encrypted using AWS KMS
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Access Controls**: IAM roles with least-privilege policies
- **Audit Logging**: Comprehensive activity tracking
- **PII Protection**: Automated detection and masking
- **Data Quality**: Schema validation and integrity checks

## 📚 Documentation

- **Architecture**: `docs/architecture.md`
- **Security**: `docs/security.md`
- **API Reference**: `docs/api.md`
- **Troubleshooting**: `docs/troubleshooting.md`

## 🆘 Troubleshooting

### Common Issues

1. **Airflow won't start**
   - Check Python version (3.8+ required)
   - Verify all dependencies are installed
   - Check database connection

2. **AWS deployment fails**
   - Verify AWS credentials are configured
   - Check IAM permissions
   - Ensure CDK is bootstrapped

3. **DAG fails to run**
   - Check Airflow connections
   - Verify environment variables
   - Review DAG logs in Airflow UI

### Getting Help

- Check the logs in Airflow UI
- Review the troubleshooting guide
- Check AWS CloudWatch logs
- Review the documentation in `docs/`

## 🎯 Next Steps

1. **Customize Configuration**: Update settings for your environment
2. **Add Data Sources**: Configure SFTP/API connections
3. **Set Up Monitoring**: Configure alerts and notifications
4. **Test Thoroughly**: Run end-to-end tests
5. **Deploy to Production**: Follow production deployment guide

## 📞 Support

For questions or issues:

1. Check the documentation in `docs/`
2. Review the troubleshooting guide
3. Check the demo script: `./scripts/demo.sh`

---

**Note**: This is a development setup. For production deployment, please follow the production deployment guide and ensure all security measures are properly configured. 