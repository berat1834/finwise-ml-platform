#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AWS Credentials Configuration Helper
Guides user through AWS credential setup
"""

print("""
================================================================================
AWS CREDENTIALS CONFIGURATION GUIDE
================================================================================

To deploy to AWS, you need AWS credentials (Access Key ID + Secret Key).

STEP 1: Get AWS Credentials from Console
================================================================================

1. Go to: https://console.aws.amazon.com
2. Login with your AWS account
3. Click on your account name (top right) → Security credentials
4. Click "Access keys" → "Create access key"
5. Choose: Application running outside AWS
6. Save the credentials:
   - Access Key ID: AKIA... (keep safe!)
   - Secret Access Key: xxxx... (keep safe!)

IMPORTANT: These are AWS account credentials - NEVER share or commit to GitHub!

================================================================================
STEP 2: Create Credentials File (Windows)
================================================================================

AWS SDK looks for credentials in: C:\\Users\\%USERNAME%\\.aws\\credentials

Run this to create it:

mkdir C:\\Users\\%USERNAME%\\.aws

Then create file: C:\\Users\\%USERNAME%\\.aws\\credentials

Content should be:

[default]
aws_access_key_id = AKIA...
aws_secret_access_key = xxxx...

[profile_name]
aws_access_key_id = AKIA...
aws_secret_access_key = xxxx...

================================================================================
STEP 3: Create AWS Config File (Windows)
================================================================================

File: C:\\Users\\%USERNAME%\\.aws\\config

Content:

[default]
region = eu-central-1
output = json

[profile profile_name]
region = eu-central-1
output = json

================================================================================
STEP 4: Verify Setup
================================================================================

Python script will check:
  from boto3.session import Session
  session = Session()
  print(session.get_credentials())

Should output your credentials (masked).

================================================================================
SECURITY BEST PRACTICES
================================================================================

1. NEVER hardcode credentials in Python scripts
2. NEVER commit .aws/credentials to Git
3. Use IAM roles when running in AWS (instead of keys)
4. Rotate access keys every 90 days
5. Use MFA for AWS console login
6. Store secrets in AWS Secrets Manager

================================================================================

Ready to configure? 

Option A: Manual - Create files above and run AWS SDK test
Option B: Python - Use script to guide setup step-by-step

Select: A or B?

================================================================================
""")
