# FinWise ML Platform — Agent Instructions

## Quick Start (How to Launch the Project)

### Prerequisites
- Python 3.9+ with `.venv` virtual environment at project root
- Node.js 18+ with npm

### Start Both Services (Recommended)

**On Windows (PowerShell):**
```powershell
# Backend (runs in background)
Start-Process -NoNewWindow -FilePath ".venv\Scripts\python.exe" -ArgumentList "backend\start.py" -WorkingDirectory "."

# Wait 3 seconds for backend to boot, then start frontend
Start-Sleep -Seconds 3
cd frontend; npm run dev
```

**Or start each separately:**

#### 1. Backend (Flask API — port 5000)
```powershell
# IMPORTANT: Use start.py, NOT app_v2_secure.py directly
# start.py handles os.chdir to backend/ and loads .env properly
.venv\Scripts\python.exe backend\start.py
```

#### 2. Frontend (Next.js — port 3000)
```powershell
cd frontend
npm install   # only needed first time
npm run dev
```

### Verify Services
- Backend health: `curl http://localhost:5000/health`
- Frontend: Open `http://localhost:3000` in browser
- Backend Swagger: `http://localhost:5000/apidocs`

## ⚠️ Critical Rules

### Startup
- **ALWAYS** use `backend/start.py` to launch the backend — it sets the correct working directory
- **NEVER** run `python backend/app_v2_secure.py` from the project root — model paths and .env won't resolve
- Backend .env is at `backend/.env` (SQLite dev mode by default, no PostgreSQL needed for local dev)
- Frontend .env is at `frontend/.env.local` (sets `NEXT_PUBLIC_API_URL=http://localhost:5000`)

### Architecture
- `backend/app_v2_secure.py` is the ONLY backend entry point
- `frontend/` (Next.js 16) is the ONLY frontend
- Backend uses JWT Bearer tokens (not HttpOnly cookies yet)
- CORS is configured in `app_v2_secure.py` — `localhost:3000` and `localhost:3001` are allowed
- ML model file: `backend/production_model.joblib` (~187MB)

### Code Changes
- All backend routes must be Flask Blueprints
- All frontend components must be TypeScript
- Never hardcode credentials — use environment variables
- Keep Turkish UI labels in the frontend
- Run `black` and `ruff` before committing Python code

### Database
- **Local dev**: SQLite (`backend/.env` → `DATABASE_URL=sqlite:///finwise_credit.db`)
- **Production**: PostgreSQL (`docker-compose.production.yml`)
- ORM models are in `backend/app/models/models.py`

### Testing
- Backend: `cd backend && python -m pytest tests/ -v`
- Frontend lint: `cd frontend && npm run lint`
- E2E: `cd frontend && npx playwright test`
