#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { HipaaEtlStack } from '../lib/hipaa-etl-stack';

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

// Create the main HIPAA ETL stack
new HipaaEtlStack(app, 'HipaaEtlStack', {
  env,
  description: 'HIPAA-compliant ETL pipeline infrastructure',
  tags: {
    Environment: 'production',
    Compliance: 'HIPAA',
    Project: 'ETL-Pipeline',
  },
});

app.synth(); 