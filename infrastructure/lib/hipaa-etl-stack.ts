import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as glue from 'aws-cdk-lib/aws-glue';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as cloudtrail from 'aws-cdk-lib/aws-cloudtrail';
import { Construct } from 'constructs';

export class HipaaEtlStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC for secure networking
    const vpc = new ec2.Vpc(this, 'HipaaVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          cidrMask: 28,
          name: 'Database',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    // KMS key for encryption
    const encryptionKey = new kms.Key(this, 'HipaaEncryptionKey', {
      enableKeyRotation: true,
      description: 'KMS key for HIPAA-compliant data encryption',
      keyUsage: kms.KeyUsage.ENCRYPT_DECRYPT,
      keySpec: kms.KeySpec.SYMMETRIC_DEFAULT,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // S3 bucket for data lake with encryption
    const dataLakeBucket = new s3.Bucket(this, 'HipaaDataLake', {
      versioned: true,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          id: 'DeleteIncompleteMultipartUploads',
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
      ],
    });

    // RDS instance for processed data
    const database = new rds.DatabaseInstance(this, 'HipaaDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_4,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc: vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
      storageEncrypted: true,
      storageEncryptionKey: encryptionKey,
      backupRetention: cdk.Duration.days(30),
      deletionProtection: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      credentials: rds.Credentials.fromGeneratedSecret('postgres'),
      databaseName: 'hipaa_etl',
    });

    // Lambda function for S3 event processing
    const s3ProcessorLambda = new lambda.Function(this, 'S3ProcessorLambda', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../lambda/s3-processor'),
      vpc: vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      environment: {
        DATABASE_SECRET_ARN: database.secret?.secretArn || '',
        GLUE_DATABASE_NAME: 'hipaa_catalog',
        GLUE_TABLE_NAME: 'processed_data',
      },
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
    });

    // Grant Lambda permissions
    database.grantConnect(s3ProcessorLambda);
    dataLakeBucket.grantRead(s3ProcessorLambda);
    encryptionKey.grantDecrypt(s3ProcessorLambda);

    // S3 event notification
    dataLakeBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(s3ProcessorLambda),
      { suffix: '.csv' }
    );

    // Glue database for data catalog
    const glueDatabase = new glue.CfnDatabase(this, 'HipaaGlueDatabase', {
      catalogId: this.account,
      databaseInput: {
        name: 'hipaa_catalog',
        description: 'Data catalog for HIPAA-compliant ETL pipeline',
      },
    });

    // CloudTrail for audit logging
    const cloudTrail = new cloudtrail.Trail(this, 'HipaaCloudTrail', {
      bucket: dataLakeBucket,
      includeGlobalServiceEvents: true,
      isMultiRegionTrail: true,
      enableLogFileValidation: true,
      encryptionKey: encryptionKey,
    });

    // IAM role for Airflow
    const airflowRole = new iam.Role(this, 'AirflowExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3ReadOnlyAccess'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
      ],
    });

    // Grant specific permissions
    dataLakeBucket.grantReadWrite(airflowRole);
    database.grantConnect(airflowRole);
    encryptionKey.grantEncryptDecrypt(airflowRole);

    // Outputs
    new cdk.CfnOutput(this, 'DataLakeBucketName', {
      value: dataLakeBucket.bucketName,
      description: 'S3 bucket for HIPAA data lake',
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: database.instanceEndpoint.hostname,
      description: 'RDS database endpoint',
    });

    new cdk.CfnOutput(this, 'EncryptionKeyArn', {
      value: encryptionKey.keyArn,
      description: 'KMS encryption key ARN',
    });
  }
} 