# Quick Start Guide - Local Development

## Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ installed
- Git installed

## Quick Start (5 minutes)

### 1. Setup Environment
```powershell
# Create .env file
Copy-Item .env.example .env

# Edit .env and update these critical values:
# - SECRET_KEY (generate random string)
# - JWT_SECRET_KEY (generate random string)
# - POSTGRES_PASSWORD (set secure password)
```

### 2. Train Model (First Time Only)
```powershell
# Install dependencies
pip install -r requirements.txt

# Train model
python training_pipeline.py

# This creates:
# - model.joblib (trained model)
# - model_meta.json (model metadata)
# - reference_data.csv (for drift detection)
```

### 3. Start Services
```powershell
# Option A: Simple (Development)
python start.py
# Access: http://localhost:5000

# Option B: Full Stack (Production-like)
docker-compose -f docker-compose.production.yml up -d

# Access services:
# - API: http://localhost:80
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

### 4. Test API
```powershell
# Health check
curl http://localhost/health

# Test prediction (requires JWT token)
# First, get token from /api/auth/login endpoint
```

## Available Commands

### Model Training & Analysis
```powershell
python training_pipeline.py          # Train model
python fairness_analysis.py          # Bias analysis
python monitoring_advanced.py        # Model monitoring test
python monitoring.py                 # Data drift analysis
```

### Testing
```powershell
pytest tests/ --cov=. --cov-report=html
```

### API Testing
```powershell
python test_api_v2.py               # Test secure API
python test_client.py               # Test client
```

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:80 | JWT auth required |
| Swagger Docs | http://localhost:80/api/docs | - |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |

## Troubleshooting

### Model file not found
```powershell
python training_pipeline.py
```

### Database connection error
```powershell
# Check if PostgreSQL is running
docker-compose ps

# Restart services
docker-compose restart
```

### Port already in use
```powershell
# Stop existing services
docker-compose down

# Or change ports in .env file
```

## Next Steps

1. Review `DEPLOYMENT_GUIDE.md` for production deployment
2. Check `PRODUCTION_CHECKLIST.md` for enterprise requirements
3. Configure monitoring alerts in `config/alerting_config.json`
4. Review API documentation at http://localhost/api/docs

## Support

For detailed documentation, see:
- `README_PRODUCTION.md` - Full feature documentation
- `DEPLOYMENT_GUIDE.md` - Production deployment
- `PRODUCTION_READINESS_ASSESSMENT.md` - Current status
