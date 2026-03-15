#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AWS Deployment Pre-flight Checklist Generator
Creates step-by-step deployment plan based on current environment
"""
from datetime import datetime

CHECKLIST = """
================================================================================
  AWS DEPLOYMENT PRE-FLIGHT CHECKLIST
  FinWise-ML Production Deployment
================================================================================

Generated: 2026-03-05
Target: Production Deployment Week 2
Estimate: 2-3 days to fully operational

================================================================================

PHASE 1: PRE-DEPLOYMENT (TODAY - TOMORROW)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 1A: Local Validation
  
  □ Task 1.1: Run all tests locally
    Command: .\\run_all_checks.ps1 -Strict
    Expected: SLA ✓, Drift ✓, Multi-tenant ✓
    
  □ Task 1.2: Verify Docker build
    Command: docker build -f Dockerfile.production -t finwise-api:local .
    Expected: Build success, image size < 500MB
    
  □ Task 1.3: Test Docker container locally
    Command: docker run -p 5000:5000 -e DATABASE_URL=sqlite finwise-api:local
    Expected: API responds to /health endpoint
    
  □ Task 1.4: Review production model
    Command: python validate_model.py
    Expected: AUC 0.9198 ✓, Fairness DI Ratio 0.628 (target: ≥0.80)

▶ PHASE 1B: AWS Credentials Setup
  
  □ Task 1.5: Install AWS CLI v2
    Command: choco install awscli -y (Windows) OR aws-cli (macOS)
    Expected: aws --version returns v2.x.x
    
  □ Task 1.6: Configure AWS credentials
    Command: aws configure
    Inputs:
      Access Key ID: [Get from AWS IAM console]
      Secret Key: [KEEP SECURE - store in .env.local]
      Region: eu-central-1 (Europe - low latency)
      Output: json
    
  □ Task 1.7: Verify AWS access
    Command: aws sts get-caller-identity
    Expected: Shows your AWS account ID, user ARN

▶ PHASE 1C: AWS Infrastructure Planning
  
  □ Task 1.8: Create RDS parameter group
    Service: AWS RDS
    Type: PostgreSQL 15
    Parameters:
      - Allocated Storage: 100 GB
      - Instance Class: db.t3.medium (adjustable)
      - Multi-AZ: YES (for 99.95% uptime)
      - Backups: 30 days retention
      - Encryption: Enabled
    
  □ Task 1.9: Create ECS cluster
    Service: AWS ECS
    Type: Fargate (serverless)
    Cluster Name: finwise-prod
    VPC: Default (or custom VPC)
    
  □ Task 1.10: Create Application Load Balancer
    Service: AWS ELB
    Type: Application Load Balancer
    Name: finwise-alb
    Listeners: 
      - HTTP (80) → HTTPS (443) redirect
      - HTTPS (443) → ECS (5000)
    Health Check: /health (threshold: 3 passes, 2 failures)

═══════════════════════════════════════════════════════════════════════════════

PHASE 2: DATABASE SETUP (TOMORROW - DAY 2)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 2A: RDS Provisioning
  
  □ Task 2.1: Create RDS instance
    Command: See AWS_DEPLOYMENT_GUIDE.md §STEP 2.1
    Time: ~5-10 minutes
    Verify: aws rds describe-db-instances --db-instance-identifier finwise-prod-db
    
  □ Task 2.2: Create security group for RDS
    Service: AWS EC2 → Security Groups
    Inbound Rules:
      - PostgreSQL (5432) from ALB security group
    
  □ Task 2.3: Store credentials securely
    Service: AWS Secrets Manager
    Create Secret: finwise/database/prod
    Values:
      - host: [RDS endpoint]
      - username: finwise_admin
      - password: [RANDOM_PASSWORD_20_CHARS+]
      - database: finwise_credit
    
  □ Task 2.4: Initialize database schema
    Command: See AWS_DEPLOYMENT_GUIDE.md §STEP 2.2
    SQL:
      CREATE DATABASE finwise_credit;
      CREATE USER finwise_app WITH PASSWORD '[PASSWORD]';
      GRANT CONNECT ON DATABASE finwise_credit TO finwise_app;
    
  □ Task 2.5: Run Alembic migrations
    Prerequisite: Alembic setup in project
    Command: alembic upgrade head
    Verify: psql connects successfully

▶ PHASE 2B: Data Migration
  
  □ Task 2.6: Export SQLite data (current)
    Command: sqlite3 finwise.db ".dump" > database.sql
    
  □ Task 2.7: Transform for PostgreSQL
    Tool: pgloader or manual conversion
    Tables: applications, decisions, users, manual_overrides, sla_metrics, etc.
    
  □ Task 2.8: Import to RDS PostgreSQL
    Command: psql -h [RDS_HOST] -U finwise_app finwise_credit < cleaned_data.sql
    
  □ Task 2.9: Verify data integrity
    Command: 
      SELECT COUNT(*) FROM applications;
      SELECT COUNT(*) FROM decisions;
    Expected: Match original SQLite counts

═══════════════════════════════════════════════════════════════════════════════

PHASE 3: CONTAINER & REGISTRY (DAY 2)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 3A: ECR Registry
  
  □ Task 3.1: Create ECR repository
    Service: AWS ECR
    Repository Name: finwise-api
    Scan on Push: YES
    Encryption: KMS (optional, for highly sensitive)
    
  □ Task 3.2: Get ECR login token
    Command: aws ecr get-login-password | docker login ...
    Expected: Login Succeeded message
    
  □ Task 3.3: Build Docker image
    Command: docker build -f Dockerfile.production -t finwise-api:latest .
    Expected: Build success, image ~350MB
    
  □ Task 3.4: Tag image for ECR
    Command: docker tag finwise-api:latest [ACCOUNT].dkr.ecr.eu-central-1.amazonaws.com/finwise-api:v1.0.0
    
  □ Task 3.5: Push to ECR
    Command: docker push [ACCOUNT].dkr.ecr.eu-central-1.amazonaws.com/finwise-api:v1.0.0
    Time: ~2-5 minutes depending on internet
    
  □ Task 3.6: Verify in ECR console
    Service: AWS ECR
    Check: Image scanned, no critical vulnerabilities

═══════════════════════════════════════════════════════════════════════════════

PHASE 4: ECS DEPLOYMENT (DAY 3)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 4A: ECS Task Definition
  
  □ Task 4.1: Create Task Definition (JSON)
    Service: AWS ECS → Task Definitions
    Template: See AWS_DEPLOYMENT_GUIDE.md §STEP 4.2
    Key Settings:
      - Family: finwise-api
      - Image: [ECR_URI]:v1.0.0
      - Memory: 512 MB (adjustable)
      - CPU: 256 units
      - Port Mapping: 5000 → 5000
      - Environment Variables:
        DATABASE_URL: (from Secrets Manager)
        FLASK_ENV: production
        JWT_SECRET: (from Secrets Manager)
      - Logging: CloudWatch
      - Capacity Provider: FARGATE
    
  □ Task 4.2: Create Task Execution Role
    Service: AWS IAM
    Permissions:
      - ECR pull (AmazonEC2ContainerRegistryReadOnly)
      - Secrets Manager (GetSecretValue)
      - CloudWatch Logs (PutLogEvents)

▶ PHASE 4B: ECS Service
  
  □ Task 4.3: Create ECS Service
    Service: AWS ECS → Services
    Cluster: finwise-prod
    Task Definition: finwise-api:1
    Launch Type: FARGATE
    Desired Count: 2 (redundancy)
    
  □ Task 4.4: Configure scaling
    Min Tasks: 2
    Max Tasks: 4
    Scale Up: If CPU > 70% for 1 minute
    Scale Down: If CPU < 30% for 5 minutes
    
  □ Task 4.5: Attach Load Balancer
    Target Group: Create new
    Health Check Path: /health
    Health Check Interval: 30 seconds
    
  □ Task 4.6: Verify service is running
    Command: aws ecs describe-services --cluster finwise-prod --services finwise-api
    Expected: Running count = 2 (or desired count)

═══════════════════════════════════════════════════════════════════════════════

PHASE 5: LOAD BALANCER & DNS (DAY 3)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 5A: ALB Configuration
  
  □ Task 5.1: Create ALB listeners
    Service: AWS ELB
    Port 80 (HTTP):
      Action: Redirect to HTTPS (port 443)
    Port 443 (HTTPS):
      SSL Certificate: ACM certificate (finwise-api.example.com)
      Target Group: finwise-api ECS targets
      
  □ Task 5.2: Verify ALB health checks
    Service: AWS ELB → Target Groups
    Expected: All 2 instances showing "healthy"
    
  □ Task 5.3: Test API through ALB
    Command: curl -k https://[ALB_dns]/health
    Expected: 200 OK response

▶ PHASE 5B: DNS & HTTPS
  
  □ Task 5.4: Request SSL certificate
    Service: AWS ACM (Certificate Manager)
    Domain: api.finwise.example.com
    Validation: DNS CNAME
    
  □ Task 5.5: Create Route 53 DNS record
    Service: AWS Route 53
    Type: CNAME or Alias
    Name: api.finwise.example.com
    Target: [ALB DNS name]
    
  □ Task 5.6: Test HTTPS endpoint
    Command: curl https://api.finwise.example.com/health
    Expected: 200 OK response with valid certificate

═══════════════════════════════════════════════════════════════════════════════

PHASE 6: MONITORING & ALARMS (DAY 3)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 6A: CloudWatch Metrics
  
  □ Task 6.1: Set up CloudWatch log groups
    Service: AWS CloudWatch Logs
    Log Groups:
      - /ecs/finwise-api (from ECS)
      - /rds/finwise-prod-db (RDS logs)
    
  □ Task 6.2: Create custom metrics
    Metrics to track:
      - API response time (ms)
      - Error rate (%)
      - Model prediction latency (ms)
      - Database connection pool usage
      - Fairness metrics (Q1, Q5 approval rates)
    
  □ Task 6.3: Create CloudWatch dashboard
    Widgets:
      - API request count
      - Response time distribution
      - Error rate over time
      - ECS CPU/Memory usage
      - RDS CPU/Database connections
      - Custom fairness metrics

▶ PHASE 6B: Alarms
  
  □ Task 6.4: Create alarm - API errors > 5%
    Threshold: ErrorRate > 5% for 5 minutes
    Action: SNS notification to ops team
    
  □ Task 6.5: Create alarm - Response time > 500ms
    Threshold: P95 Response Time > 500ms
    Action: SNS + Auto-scaling up
    
  □ Task 6.6: Create alarm - Low fairness
    Threshold: Q1 approval rate < 1%
    Action: SNS notification + Investigation alert
    
  □ Task 6.7: Create alarm - RDS CPU > 80%
    Threshold: CPU > 80% for 10 minutes
    Action: SNS + Consider upgrading instance
    
  □ Task 6.8: Create alarm - Disk full (RDS)
    Threshold: Free space < 10%
    Action: SNS + Automated snapshot

═══════════════════════════════════════════════════════════════════════════════

PHASE 7: SECURITY & COMPLIANCE (DAY 3)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 7A: Network Security
  
  □ Task 7.1: Review RDS security groups
    Inbound: PostgreSQL (5432) only from ALB
    Outbound: All (typical)
    
  □ Task 7.2: Review ECS task security groups
    Inbound: From ALB on port 5000 only
    Outbound: RDS, ECR, S3, CloudWatch
    
  □ Task 7.3: Review ALB security groups
    Inbound: HTTP (80) and HTTPS (443) from Internet
    Outbound: To ECS tasks (5000)

▶ PHASE 7B: Secrets Management
  
  □ Task 7.4: Verify JWT secret in Secrets Manager
    Service: AWS Secrets Manager
    Secret: finwise/api/jwt-secret
    Rotation: Enable automatic rotation (30 days)
    
  □ Task 7.5: Verify Database credentials
    Service: AWS Secrets Manager
    Secret: finwise/database/prod
    Rotation: Enable (14 days)
    
  □ Task 7.6: Audit IAM permissions
    Service: AWS IAM Access Analyzer
    Review: ECS task role has minimum required permissions

▶ PHASE 7C: API Security
  
  □ Task 7.7: Enable WAF (Web Application Firewall)
    Service: AWS WAF
    Attach: To ALB
    Rules:
      - Rate limiting (1000 req/5min per IP)
      - SQL injection protection
      - XSS protection
      - Geographic restrictions (optional)
    
  □ Task 7.8: Enable API logging
    Feature: CloudTrail (for audit trail)
    CloudWatch: All requests logged with status

═══════════════════════════════════════════════════════════════════════════════

PHASE 8: FINAL VALIDATION (DAY 3)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 8A: Smoke Tests
  
  □ Task 8.1: Health check endpoint
    Command: curl https://api.finwise.example.com/health
    Expected: 200 OK
    
  □ Task 8.2: Login endpoint
    Command: curl -X POST https://api.finwise.example.com/login \\
             -H "Content-Type: application/json" \\
             -d '{"email":"test@example.com","password":"test"}'
    Expected: 200 or 401 (auth error, not server error)
    
  □ Task 8.3: Prediction endpoint
    Command: curl -X POST https://api.finwise.example.com/degerlendir \\
             -H "Authorization: Bearer [TOKEN]" \\
             -H "Content-Type: application/json" \\
             -d '{...loan_data...}'
    Expected: 200 with prediction + SHAP explanation
    
  □ Task 8.4: Performance test
    Tool: Apache Bench or wrk
    Command: wrk -t4 -c100 -d30s https://api.finwise.example.com/health
    Expected: P95 response time < 200ms, error rate < 1%
    
  □ Task 8.5: JWT authentication test
    Verify: Token expires, refresh works, invalid token rejected
    
  □ Task 8.6: CORS headers verify
    Expected: Proper CORS headers for client origin

▶ PHASE 8B: Database Tests
  
  □ Task 8.7: Database connectivity
    Command: psql -h [RDS_HOST] -U finwise_app -c "SELECT COUNT(*) FROM applications;"
    Expected: Returns count > 0
    
  □ Task 8.8: Backup verification
    Service: AWS RDS
    Check: Automated backups running, latest backup recent

═══════════════════════════════════════════════════════════════════════════════

PHASE 9: PILOT CUSTOMER PREP (READY FOR ONBOARDING)
═══════════════════════════════════════════════════════════════════════════════

▶ PHASE 9A: Documentation
  
  □ Task 9.1: Create API documentation (Swagger)
    Service: Built-in from Flask-RESTX
    URL: https://api.finwise.example.com/docs
    Review: All endpoints documented, auth examples provided
    
  □ Task 9.2: Create deployment runbook
    Content:
      - How to monitor API
      - How to scale
      - How to rollback
      - Emergency contacts
    
  □ Task 9.3: Create fairness monitoring guide
    Content:
      - How to check fairness metrics
      - Alerts and thresholds
      - What to do if Q1 approval < 2%

▶ PHASE 9B: Pilot Customer Onboarding
  
  □ Task 9.4: Get customer approval
    Requirements:
      - Data sharing agreement signed
      - API access credentials provisioned
      - Fairness monitoring explained
    
  □ Task 9.5: Create customer environment
    AWS: Create separate multi-tenant credentials
    Database: Create customer schema (finwise_credit.customer_001)
    
  □ Task 9.6: Run pilot validation
    Duration: 1-2 weeks
    Target: 500-1000 loan decisions
    Metrics Collected:
      - Real data fairness (Q1 vs Q5 approval rates)
      - Model AUC on real data
      - API performance
      - User feedback

═══════════════════════════════════════════════════════════════════════════════

📊 SUMMARY

Total Estimated Time:
  • Phase 1 (Local): 2-4 hours
  • Phase 2 (Database): 2-4 hours
  • Phase 3 (Docker): 1-2 hours
  • Phase 4-8 (AWS): 4-6 hours
  • TOTAL: 9-16 hours spread over 3 days

Cost Estimates (AWS):
  • RDS db.t3.medium: ~$100/month
  • ECS 2 tasks: ~$30/month
  • ALB: ~$16/month
  • Data transfer: ~$10/month
  • Total: ~$156/month for minimal setup
  • Scaling 4x: ~$300/month

Risk Mitigation:
  ✓ Database backups (30 days)
  ✓ Auto-scaling (up to 4 replicas)
  ✓ Fairness monitoring (alerts on discrimination)
  ✓ Health checks (instant failover)
  ✓ Secrets management (no hardcoded credentials)

Dependencies:
  ✓ AWS account with permissions
  ✓ Docker installed
  ✓ AWS CLI configured
  ✓ PostgreSQL knowledge (basic)
  ✓ Understanding of RDS/ECS (or learn on the job)

═══════════════════════════════════════════════════════════════════════════════

🎯 NEXT IMMEDIATE ACTION

Choose ONE option:

Option A: AUTOMATED SETUP (Recommended if AWS experience)
  → Run: python aws_deploy_auto.py
  → Creates all resources with single script
  → Estimated time: 30 minutes

Option B: MANUAL STEP-BY-STEP
  → Follow PHASE 1A-B (today: 2 hours)
  → Then continue with remaining phases
  → Estimated time: 12-15 hours over 3 days

Option C: GUIDED WALKTHROUGH
  → Get AWS console walkthrough
  → Ask questions as you go
  → Estimated time: 8-10 hours over 3 days

═══════════════════════════════════════════════════════════════════════════════

Questions or clarifications needed? 

Next: Run Phase 1A local tests to confirm readiness!

"""

if __name__ == "__main__":
    print(CHECKLIST)
    with open("AWS_DEPLOYMENT_CHECKLIST.txt", "w") as f:
        f.write(CHECKLIST)
    print("\n✓ Checklist saved to AWS_DEPLOYMENT_CHECKLIST.txt")
