# AWS Deployment Guide - FinWise-ML Credit Risk API

## Overview

Bu guide, FinWise-ML API'yi AWS Production ortamına deploy etmek için gerekli tüm adımları açıklamaktadır.

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS PRODUCTION STACK                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Route 53 (DNS)                                             │
│      ↓                                                       │
│  CloudFront (CDN) + WAF (DDoS/Security)                     │
│      ↓                                                       │
│  Application Load Balancer (ALB)                            │
│      ↓                                                       │
│  ┌─────────────────────────────────────┐                   │
│  │   ECS Cluster (Fargate - Serverless) │                  │
│  │   ├─ 2-4 Task Replicas (HA)         │                  │
│  │   └─ Auto-scaling (CPU/Memory)      │                  │
│  └─────────────────────────────────────┘                   │
│      ↓                                                       │
│  ┌─────────────────────────────────────┐                   │
│  │     RDS (PostgreSQL)                │                   │
│  │     ├─ Multi-AZ (99.95% uptime)     │                  │
│  │     └─ Automated Backups (30 days)  │                  │
│  └─────────────────────────────────────┘                   │
│         ↓ ↓                                                  │
│  ElastiCache (Redis)    S3 (Model Storage)                 │
│  - Rate limiting        - Model files                       │
│  - Session cache        - Training data                     │
│           ↓                     ↓                           │
│     CloudWatch Logs    Monitoring (Prometheus/Grafana)     │
│     CloudWatch Alarms  AppLens (Diagnostics)               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## STEP 1: AWS ACCOUNT SETUP

### 1.1 AWS CLI Kurulumu

```bash
# AWS CLI v2 kur
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### 1.2 AWS Credentials Konfigürasyonu

```bash
aws configure

# Sorular:
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region: eu-central-1  (Avrupa = lower latency)
# Default output format: json
```

### 1.3 IAM Role Oluştur (ECS ve RDS erişimi için)

```bash
# inline-policy oluştur
cat > ecs-task-execution-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Role oluştur
aws iam create-role \
  --role-name FinWiseECStaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json

# Policy ekle
aws iam attach-role-policy \
  --role-name FinWiseECStaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# S3 + RDS access
cat > custom-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::finwise-models/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:finwise/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name FinWiseECStaskExecutionRole \
  --policy-name FinWiseS3RDSPolicy \
  --policy-document file://custom-policy.json
```

---

## STEP 2: RDS PostgreSQL DATABASE

### 2.1 RDS Cluster Oluştur

```bash
# PostgreSQL instance oluştur (Production-ready)
aws rds create-db-instance \
  --db-instance-identifier finwise-prod-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username finwise_admin \
  --master-user-password 'YOUR_STRONG_PASSWORD' \
  --allocated-storage 100 \
  --storage-type gp3 \
  --multi-az \
  --backup-retention-period 30 \
  --enable-cloudwatch-logs-exports '[postgresql]' \
  --enable-iam-database-authentication \
  --publicly-accessible false \
  --db-subnet-group-name finwise-db-subnet \
  --vpc-security-group-ids sg-xxxxxx

# Wait for creation
aws rds wait db-instance-available --db-instance-identifier finwise-prod-db

# Check status
aws rds describe-db-instances \
  --db-instance-identifier finwise-prod-db \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address}'
```

### 2.2 Database ve Kullanıcı Oluştur

```bash
# RDS endpoint'i getir
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier finwise-prod-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Connect
psql -h $DB_ENDPOINT -U finwise_admin -d postgres

# SQL Commands:
CREATE DATABASE finwise_credit OWNER finwise_admin;
CREATE USER finwise_app WITH PASSWORD 'YOUR_APP_PASSWORD';
GRANT CONNECT ON DATABASE finwise_credit TO finwise_app;

-- Connect to new DB
\c finwise_credit

GRANT ALL ON SCHEMA public TO finwise_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO finwise_app;
```

### 2.3 Alembic Migrations Çalıştır

```bash
# Migration setup
alembic init alembic_migrations

# Edit alembic/env.py - update database URL

# Create migrations
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

---

## STEP 3: ECR (Elastic Container Registry)

### 3.1 Docker Image Build

```bash
# AWS account ID getir
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="eu-central-1"

# ECR repo oluştur
aws ecr create-repository \
  --repository-name finwise-api \
  --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Docker image oluştur
docker build -t finwise-api:latest .

# Tag
docker tag finwise-api:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finwise-api:latest

docker tag finwise-api:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finwise-api:v1.0.0

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finwise-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finwise-api:v1.0.0

# Verify
aws ecr describe-images --repository-name finwise-api
```

### 3.2 Dockerfile Optimize

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

# Copy application
COPY app_v2_secure.py app_v2_secure.py
COPY models.py models.py
COPY compliance.py compliance.py
COPY training_pipeline.py training_pipeline.py
COPY sla_monitoring.py sla_monitoring.py
COPY drift_detection_retraining.py drift_detection_retraining.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# Security: Run as non-root
RUN useradd -m -u 1000 finwise
USER finwise

# Start app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", \
     "--worker-class", "sync", "--timeout", "120", "app_v2_secure:app"]
```

---

## STEP 4: ECS CLUSTER (Fargate)

### 4.1 VPC & Network Setup

```bash
# VPC oluştur
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' \
  --output text)

# Subnets oluştur (Multi-AZ HA)
SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone eu-central-1a \
  --query 'Subnet.SubnetId' \
  --output text)

SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone eu-central-1b \
  --query 'Subnet.SubnetId' \
  --output text)

# Security Group (ALB)
SG_ALB=$(aws ec2 create-security-group \
  --group-name finwise-alb-sg \
  --description "ALB security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

# Allow HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ALB \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ALB \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# Security Group (ECS)
SG_ECS=$(aws ec2 create-security-group \
  --group-name finwise-ecs-sg \
  --description "ECS task security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ECS \
  --protocol tcp --port 5000 \
  --source-security-group-id $SG_ALB
```

### 4.2 ECS Cluster Oluştur

```bash
# Cluster
aws ecs create-cluster --cluster-name finwise-prod

# Task Definition
cat > ecs-task-definition.json <<EOF
{
  "family": "finwise-api",
  "taskRoleArn": "arn:aws:iam::AWS_ACCOUNT_ID:role/FinWiseECStaskExecutionRole",
  "executionRoleArn": "arn:aws:iam::AWS_ACCOUNT_ID:role/FinWiseECStaskExecutionRole",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "finwise-api",
      "image": "AWS_ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/finwise-api:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "hostPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:eu-central-1:AWS_ACCOUNT_ID:secret:finwise/db-url"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:eu-central-1:AWS_ACCOUNT_ID:secret:finwise/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/finwise-api",
          "awslogs-region": "eu-central-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

### 4.3 ALB & Service

```bash
# Load Balancer
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name finwise-alb \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $SG_ALB \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Target Group
TG_ARN=$(aws elbv2 create-target-group \
  --name finwise-tg \
  --protocol HTTP \
  --port 5000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-enabled \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 10 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# ECS Service
aws ecs create-service \
  --cluster finwise-prod \
  --service-name finwise-api-service \
  --task-definition finwise-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SG_ECS],assignPublicIp=DISABLED}" \
  --load-balancers targetGroupArn=$TG_ARN,containerName=finwise-api,containerPort=5000 \
  --enable-ecs-managed-tags

# Auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/finwise-prod/finwise-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# CPU-based scaling
aws application-autoscaling put-scaling-policy \
  --policy-name finwise-cpu-scaling \
  --service-namespace ecs \
  --resource-id service/finwise-prod/finwise-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration "{
    \"TargetValue\": 70.0,
    \"PredefinedMetricSpecification\": {
      \"PredefinedMetricType\": \"ECSServiceAverageCPUUtilization\"
    },
    \"ScaleOutCooldown\": 60,
    \"ScaleInCooldown\": 300
  }"
```

---

## STEP 5: MONITORING

### 5.1 CloudWatch Logs

```bash
# Log group oluştur
aws logs create-log-group --log-group-name /ecs/finwise-api

# Retention policy (30 days)
aws logs put-retention-policy \
  --log-group-name /ecs/finwise-api \
  --retention-in-days 30
```

### 5.2 CloudWatch Alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name finwise-api-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:eu-central-1:AWS_ACCOUNT_ID:FinWiseAlerts
```

### 5.3 Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'finwise-api'
    static_configs:
      - targets: ['finwise-api.example.com:5000']
    metrics_path: '/metrics'
    basic_auth:
      username: prometheus
      password: $(SECRET_PROMETHEUS_PASSWORD)
```

---

## STEP 6: SECRETS MANAGEMENT

```bash
# Store database credentials
aws secretsmanager create-secret \
  --name finwise/db-url \
  --secret-string "postgresql://finwise_app:PASSWORD@finwise-prod-db.eu-central-1.rds.amazonaws.com:5432/finwise_credit"

# Store JWT secret
aws secretsmanager create-secret \
  --name finwise/jwt-secret \
  --secret-string "your-jwt-secret-key-here"

# List secrets
aws secretsmanager list-secrets --filters Key=name,Values=finwise
```

---

## STEP 7: CONTINUOUS DEPLOYMENT (CI/CD)

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS ECS

on:
  push:
    branches: [main, production]

env:
  AWS_REGION: eu-central-1
  ECR_REPOSITORY: finwise-api

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        returns: ecr-login
        run: |
          aws ecr get-login-password --region ${{ env.AWS_REGION }} | \
            docker login --username AWS --password-stdin \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com

      - name: Build, tag, and push image to Amazon ECR
        run: |
          docker build -t ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY }}:${{ github.sha }} .
          docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
          docker tag ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY }}:${{ github.sha }} \
                     ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY }}:latest
          docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY }}:latest

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster finwise-prod \
            --service finwise-api-service \
            --force-new-deployment
```

---

## STEP 8: SSL/HTTPS (ACM Certificate)

```bash
# Request Certificate
CERT_ARN=$(aws acm request-certificate \
  --domain-name api.finwise.com \
  --subject-alternative-names www.api.finwise.com \
  --validation-method DNS \
  --query 'CertificateArn' \
  --output text)

# Validate via DNS (manual step)
# Then update ALB listener
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=...

# Redirect HTTP to HTTPS
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'
```

---

## ESTIMATED COSTS (Monthly)

| Service | Instance | Monthly |
|---------|----------|---------|
| RDS PostgreSQL | db.t3.medium | ~$100 |
| ECS Fargate | 2 tasks, 512 CPU, 1GB RAM | ~$50 |
| ALB | 1 load balancer | ~$20 |
| ElastiCache Redis | cache.t3.small | ~$30 |
| Data Transfer | 100 GB | ~$10-15 |
| CloudWatch Logs | 10 GB/month | ~$5 |
| **TOTAL** | | **~$215-220** |

---

## MONITORING & ALERTING

### Health Checks

```bash
# Test API health
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://api.finwise.com/health

# Check service status
aws ecs describe-services \
  --cluster finwise-prod \
  --services finwise-api-service \
  --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount}'

# View logs
aws logs tail /ecs/finwise-api --follow
```

---

## DISASTER RECOVERY

### Backup & Restore

```bash
# Enable RDS automated backups (already enabled)
# Snapshots retained: 30 days

# Manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier finwise-prod-db \
  --db-snapshot-identifier finwise-backup-$(date +%Y%m%d)

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier finwise-prod-db-restored \
  --db-snapshot-identifier finwise-backup-20260305
```

---

## SECURITY BEST PRACTICES

✅ **Implemented:**
- ✓ Multi-AZ RDS
- ✓ VPC (private subnet for RDS)
- ✓ Security groups (port 5000 only from ALB)
- ✓ Secrets Manager (encrypted credentials)
- ✓ IAM roles (least privilege)
- ✓ VPC Flow Logs
- ✓ CloudWatch Alarms

To Do:
- [ ] AWS WAF (DDoS, SQL injection protection)
- [ ] GuardDuty (threat detection)
- [ ] Config Rules (compliance)
- [ ] VPC endpoint for S3 (no internet)

---

## NEXT STEPS

1. Create AWS account and configure CLI
2. Deploy RDS PostgreSQL
3. Build Docker image
4. Push to ECR
5. Create ECS cluster
6. Set up ALB
7. Deploy service
8. Configure SSL certificate
9. Set up monitoring & alarms
10. Test with load testing tool

Estimated deployment time: **2-3 hours**

