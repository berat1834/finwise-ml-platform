# 🚀 Production Deployment Guide

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Configuration](#configuration)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This guide covers deploying the Credit Risk Analysis System to production environments. The system is production-ready with:

- ✅ **Scalability**: Kubernetes with auto-scaling (HPA)
- ✅ **High Availability**: Multiple replicas with load balancing
- ✅ **Security**: JWT authentication, rate limiting, HTTPS
- ✅ **Monitoring**: Prometheus + Grafana dashboards
- ✅ **Observability**: Structured logging, metrics, health checks
- ✅ **CI/CD**: Automated testing and deployment pipeline
- ✅ **Database**: PostgreSQL with persistent storage
- ✅ **Caching**: Redis for performance optimization
- ✅ **ML Monitoring**: Data drift detection, bias analysis

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │  (Reverse Proxy + SSL)
                    │  (Rate Limit)│
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼──────┐    ┌─────▼──────┐
   │ API Pod │      │  API Pod   │    │  API Pod   │
   │ (Flask) │      │  (Flask)   │    │  (Flask)   │
   └────┬────┘      └─────┬──────┘    └─────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼──────┐    ┌─────▼──────┐
   │PostgreSQL│      │   Redis    │    │ Prometheus │
   │   (DB)   │      │  (Cache)   │    │ (Metrics)  │
   └──────────┘      └────────────┘    └─────┬──────┘
                                              │
                                       ┌──────▼──────┐
                                       │   Grafana   │
                                       │ (Dashboard) │
                                       └─────────────┘
```

---

## 📦 Prerequisites

### Required Software
- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Kubernetes** >= 1.28 (for K8s deployment)
- **kubectl** (for K8s deployment)
- **Python** >= 3.11
- **Git**

### Optional Tools
- **Helm** (for K8s package management)
- **Terraform** (for infrastructure as code)
- **Azure CLI / AWS CLI** (for cloud deployments)

### System Requirements
- **CPU**: Minimum 4 cores (8+ recommended)
- **RAM**: Minimum 8GB (16GB+ recommended)
- **Disk**: Minimum 50GB (SSD recommended)
- **Network**: Stable internet connection for pulling images

---

## 🚀 Quick Start

### Option 1: Docker Compose (Easiest)

```powershell
# 1. Clone repository
git clone <repository-url>
cd ML-Projem

# 2. Create environment file
Copy-Item .env.example .env
# Edit .env with your configuration

# 3. Train model (if not already trained)
python training_pipeline.py

# 4. Start all services
docker-compose -f docker-compose.production.yml up -d

# 5. Check health
curl http://localhost/health

# 6. Access services
# API: http://localhost:80
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### Option 2: Kubernetes Deployment

```powershell
# 1. Configure kubectl for your cluster
kubectl config use-context <your-context>

# 2. Update secrets in k8s/secrets.yaml
# Generate base64 secrets:
# [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-secret"))

# 3. Deploy using script
python deploy.py --environment production --build --push --registry <your-registry>

# Or manually:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml

# 4. Wait for rollout
kubectl rollout status deployment/credit-risk-api -n credit-risk-system

# 5. Check pods
kubectl get pods -n credit-risk-system
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
# Security
SECRET_KEY=your-super-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this
JWT_ACCESS_TOKEN_EXPIRES=3600

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-this-password
POSTGRES_DB=credit_risk_db
POSTGRES_PORT=5432
DATABASE_URL=postgresql://postgres:password@db:5432/credit_risk_db

# Redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# API
API_PORT=5000
WORKERS=4
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=https://your-frontend.com,https://www.your-frontend.com

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=change-this-password
```

### Model Configuration

Edit `model_meta.json` for model settings:
```json
{
  "threshold": 0.191,
  "model_version": "v2.0",
  "features": [...],
  "performance": {
    "roc_auc": 0.932,
    "recall": 0.866
  }
}
```

---

## 📊 Monitoring & Observability

### Prometheus Metrics

Available at `http://localhost:9090`

Key metrics:
- `model_predictions_total` - Total predictions
- `model_rejection_rate` - Current rejection rate
- `model_dataset_drift` - Data drift score
- `model_prediction_latency_seconds` - Prediction latency
- `flask_http_request_total` - HTTP requests
- `system_cpu_usage_percent` - CPU usage
- `system_memory_usage_percent` - Memory usage

### Grafana Dashboards

Access: `http://localhost:3000` (admin/admin)

Pre-configured dashboards:
1. **API Performance** - Request rates, latency, errors
2. **Model Monitoring** - Predictions, drift, performance
3. **System Health** - CPU, memory, disk usage
4. **Database Metrics** - Query performance, connections

### Log Management

Logs are stored in:
- Container logs: `docker logs <container-name>`
- Application logs: `./logs/app.log`
- Monitoring logs: `./logs/monitoring_advanced.log`
- Kubernetes logs: `kubectl logs -n credit-risk-system <pod-name>`

```powershell
# View API logs
docker-compose logs -f api

# View last 100 lines
kubectl logs -n credit-risk-system deployment/credit-risk-api --tail=100 -f
```

---

## 🔒 Security

### SSL/TLS Configuration

For production, enable HTTPS:

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place certificates in `nginx/ssl/`:
   - `cert.pem`
   - `key.pem`
3. Uncomment HTTPS section in `nginx/nginx.conf`
4. Restart nginx

### Secrets Management

**DO NOT commit secrets to Git!**

For Kubernetes:
```powershell
# Create secrets from file
kubectl create secret generic credit-risk-secrets \
  --from-literal=SECRET_KEY='your-secret' \
  --from-literal=JWT_SECRET_KEY='your-jwt-secret' \
  --from-literal=POSTGRES_PASSWORD='your-db-password' \
  -n credit-risk-system
```

For Azure Key Vault / AWS Secrets Manager:
- Use CSI drivers for K8s secret injection
- Reference documentation in `docs/secrets-management.md`

### Network Security

1. **Firewall Rules**: Restrict access to trusted IPs
2. **Rate Limiting**: Configured in nginx (100 req/min per IP)
3. **API Authentication**: JWT required for sensitive endpoints
4. **Database**: Not exposed publicly, only internal cluster access

---

## 🔧 Maintenance

### Database Backups

```powershell
# Automated backups (add to cron/scheduled tasks)
docker exec postgres-db pg_dump -U postgres credit_risk_db > backup_$(date +%Y%m%d).sql

# Kubernetes backup
kubectl exec -n credit-risk-system postgres-0 -- \
  pg_dump -U postgres credit_risk_db > backup.sql
```

### Model Retraining

```powershell
# 1. Train new model
python training_pipeline.py

# 2. Run validation
python fairness_analysis.py
python monitoring_advanced.py

# 3. Update model in production
# Docker Compose:
docker-compose restart api

# Kubernetes:
kubectl rollout restart deployment/credit-risk-api -n credit-risk-system
```

### Scaling

```powershell
# Manual scaling (Docker Compose)
docker-compose -f docker-compose.production.yml up -d --scale api=5

# Kubernetes auto-scaling (HPA)
kubectl get hpa -n credit-risk-system
# Configured: min=3, max=10 replicas based on CPU/Memory

# Manual K8s scaling
kubectl scale deployment/credit-risk-api --replicas=5 -n credit-risk-system
```

### Updates & Rollbacks

```powershell
# Rolling update (K8s)
kubectl set image deployment/credit-risk-api \
  api=credit-risk-api:v2.1 -n credit-risk-system

# Rollback
kubectl rollout undo deployment/credit-risk-api -n credit-risk-system

# Check rollout history
kubectl rollout history deployment/credit-risk-api -n credit-risk-system
```

---

## 🐛 Troubleshooting

### Common Issues

#### API Not Responding
```powershell
# Check container status
docker-compose ps

# Check logs
docker-compose logs api

# Kubernetes
kubectl get pods -n credit-risk-system
kubectl describe pod <pod-name> -n credit-risk-system
kubectl logs <pod-name> -n credit-risk-system
```

#### Database Connection Issues
```powershell
# Test DB connection
docker exec -it postgres-db psql -U postgres -d credit_risk_db

# Check DB logs
docker-compose logs db

# Verify connection string
echo $DATABASE_URL
```

#### High Memory Usage
```powershell
# Check resource usage
docker stats

# Kubernetes
kubectl top pods -n credit-risk-system
kubectl describe node <node-name>

# Increase memory limits in deployment manifest
```

#### Model Drift Detected
```powershell
# Generate drift report
python monitoring.py

# Review bias analysis
python fairness_analysis.py

# Check alerts
curl http://localhost:9090/api/v1/alerts
```

### Health Checks

```powershell
# API Health
curl http://localhost/health

# Database
docker exec postgres-db pg_isready -U postgres

# Redis
docker exec redis redis-cli ping

# Full system check
python deploy.py --environment staging
```

---

## 📚 Additional Resources

- **API Documentation**: `http://localhost/api/docs` (Swagger UI)
- **Model Documentation**: `docs/model-documentation.md`
- **Security Guide**: `docs/security-best-practices.md`
- **Regulatory Compliance**: `docs/compliance-checklist.md`
- **Performance Tuning**: `docs/performance-optimization.md`

---

## 🆘 Support

For issues and questions:
1. Check logs and monitoring dashboards
2. Review this documentation
3. Search existing issues in repository
4. Contact: data-science-team@company.com

---

## ✅ Production Readiness Checklist

Before going live:

- [ ] SSL/TLS certificates configured
- [ ] Environment variables set (non-default passwords)
- [ ] Database backups automated
- [ ] Monitoring dashboards configured
- [ ] Alerting rules tested
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Bias analysis reviewed
- [ ] Regulatory compliance documented
- [ ] Disaster recovery plan documented
- [ ] Team trained on operations
- [ ] Documentation updated

---

## 📝 License

Copyright (c) 2025. All rights reserved.
