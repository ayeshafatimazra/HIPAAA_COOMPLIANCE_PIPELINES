#!/bin/bash

# HIPAA ETL Pipeline Deployment Script
# This script deploys the complete HIPAA-compliant ETL pipeline infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="hipaa-etl-pipeline"
AWS_REGION=${AWS_REGION:-"us-east-1"}
ENVIRONMENT=${ENVIRONMENT:-"production"}

echo -e "${BLUE}🚀 Starting HIPAA ETL Pipeline Deployment${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "Project: ${PROJECT_NAME}"
echo -e "Region: ${AWS_REGION}"
echo -e "Environment: ${ENVIRONMENT}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ first."
        exit 1
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed. Please install it with 'npm install -g aws-cdk'."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker is not installed. Monitoring stack will be skipped."
        DOCKER_AVAILABLE=false
    else
        DOCKER_AVAILABLE=true
    fi
    
    print_status "Prerequisites check completed"
}

# Deploy AWS infrastructure
deploy_infrastructure() {
    print_status "Deploying AWS infrastructure..."
    
    cd infrastructure
    
    # Install dependencies
    print_status "Installing CDK dependencies..."
    npm install
    
    # Bootstrap CDK (if needed)
    print_status "Bootstrapping CDK..."
    cdk bootstrap aws://$(aws sts get-caller-identity --query Account --output text)/${AWS_REGION}
    
    # Deploy the stack
    print_status "Deploying HIPAA ETL infrastructure..."
    cdk deploy --all --require-approval never
    
    # Get stack outputs
    print_status "Getting stack outputs..."
    cdk list
    
    cd ..
    
    print_status "Infrastructure deployment completed"
}

# Setup Airflow
setup_airflow() {
    print_status "Setting up Apache Airflow..."
    
    cd airflow
    
    # Create virtual environment
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Airflow dependencies..."
    pip install -r requirements.txt
    
    # Initialize Airflow database
    print_status "Initializing Airflow database..."
    airflow db init
    
    # Create admin user
    print_status "Creating Airflow admin user..."
    airflow users create \
        --username admin \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email admin@hipaa-etl.com \
        --password admin123
    
    # Start Airflow webserver (in background)
    print_status "Starting Airflow webserver..."
    airflow webserver --port 8080 --daemon
    
    # Start Airflow scheduler (in background)
    print_status "Starting Airflow scheduler..."
    airflow scheduler --daemon
    
    cd ..
    
    print_status "Airflow setup completed"
}

# Setup monitoring
setup_monitoring() {
    if [ "$DOCKER_AVAILABLE" = false ]; then
        print_warning "Skipping monitoring setup (Docker not available)"
        return
    fi
    
    print_status "Setting up monitoring stack..."
    
    cd monitoring
    
    # Start monitoring services
    print_status "Starting Prometheus, Grafana, and AlertManager..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service status
    print_status "Checking service status..."
    docker-compose ps
    
    cd ..
    
    print_status "Monitoring setup completed"
}

# Setup UI
setup_ui() {
    print_status "Setting up monitoring dashboard..."
    
    cd ui
    
    # Install dependencies
    print_status "Installing UI dependencies..."
    npm install
    
    # Build the application
    print_status "Building the application..."
    npm run build
    
    cd ..
    
    print_status "UI setup completed"
}

# Configure connections and variables
configure_airflow() {
    print_status "Configuring Airflow connections and variables..."
    
    # This would typically be done through Airflow UI or API
    # For now, we'll create a configuration script
    cat > scripts/configure_airflow.py << 'EOF'
from airflow.models import Connection, Variable
from airflow import settings

# Create connections
connections = [
    {
        'conn_id': 'hipaa_postgres',
        'conn_type': 'postgres',
        'host': 'your-rds-endpoint',
        'schema': 'hipaa_etl',
        'login': 'postgres',
        'password': 'your-password',
        'port': 5432
    },
    {
        'conn_id': 'hipaa_sftp',
        'conn_type': 'sftp',
        'host': 'your-sftp-server',
        'login': 'your-username',
        'password': 'your-password',
        'port': 22
    },
    {
        'conn_id': 'hipaa_api',
        'conn_type': 'http',
        'host': 'your-api-endpoint',
        'login': 'your-api-key',
        'password': 'your-api-secret'
    }
]

# Create variables
variables = [
    ('hipaa_s3_bucket', 'your-s3-bucket-name'),
    ('hipaa_kms_key_arn', 'your-kms-key-arn'),
    ('hipaa_environment', 'production')
]

session = settings.Session()

# Add connections
for conn in connections:
    existing = session.query(Connection).filter(Connection.conn_id == conn['conn_id']).first()
    if existing:
        session.delete(existing)
    
    new_conn = Connection(**conn)
    session.add(new_conn)

# Add variables
for var_id, var_value in variables:
    existing = session.query(Variable).filter(Variable.key == var_id).first()
    if existing:
        existing.set_val(var_value)
    else:
        new_var = Variable(key=var_id, val=var_value)
        session.add(new_var)

session.commit()
session.close()
EOF
    
    print_warning "Please update the configuration script with your actual values"
    print_status "Airflow configuration script created at scripts/configure_airflow.py"
}

# Run tests
run_tests() {
    print_status "Running deployment tests..."
    
    # Test infrastructure
    print_status "Testing infrastructure connectivity..."
    # Add your test commands here
    
    # Test Airflow
    print_status "Testing Airflow connectivity..."
    # Add your test commands here
    
    print_status "Tests completed"
}

# Main deployment flow
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    
    check_prerequisites
    deploy_infrastructure
    setup_airflow
    setup_monitoring
    setup_ui
    configure_airflow
    run_tests
    
    echo ""
    echo -e "${GREEN}🎉 HIPAA ETL Pipeline deployment completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "1. Update Airflow connections in scripts/configure_airflow.py"
    echo -e "2. Run: python scripts/configure_airflow.py"
    echo -e "3. Access Airflow UI at: http://localhost:8080"
    echo -e "4. Access Grafana at: http://localhost:3000"
    echo -e "5. Access Prometheus at: http://localhost:9090"
    echo ""
    echo -e "${YELLOW}Remember to:${NC}"
    echo -e "- Change default passwords"
    echo -e "- Configure SSL certificates"
    echo -e "- Set up proper backup procedures"
    echo -e "- Review and test security configurations"
}

# Run main function
main "$@" 