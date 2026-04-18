# 🚀 CodeScan AI - Deployment Guide

This guide covers deploying CodeScan AI to production using **Vercel** (frontend) and **Render** (backend).

---

## 📋 Prerequisites

Before deploying, ensure you have:

- GitHub repository with CodeScan AI code
- Vercel account (https://vercel.com)
- Render account (https://render.com)
- API keys for:
  - **Groq API** (https://console.groq.com)
  - **Google Gemini** (https://makersuite.google.com/app/apikey)
  - **Hugging Face** (optional, https://huggingface.co/settings/tokens)

---

## 🎨 Frontend Deployment (Vercel)

### Step 1: Connect GitHub Repository

1. Visit https://vercel.com/new
2. Click "Import Git Repository"
3. Select your CodeScan AI GitHub repository
4. Vercel will auto-detect it as a Vite project

### Step 2: Configure Build Settings

**Build Command:**
```bash
npm run build
```

**Output Directory:**
```
dist
```

**Root Directory:**
```
frontend
```

### Step 3: Set Environment Variables

In Vercel Project Settings → Environment Variables, add:

```env
VITE_API_URL=https://api.codescan-ai.com
VITE_SOCKET_URL=https://api.codescan-ai.com
VITE_APP_NAME=CodeScan AI
```

**For Development:**
```env
VITE_API_URL=http://localhost:5000
VITE_SOCKET_URL=http://localhost:5000
```

### Step 4: Deploy

Vercel will auto-deploy on every push to `main` branch. You can also manually trigger deployments from the Vercel dashboard.

**Your frontend will be available at:**
```
https://codescan-ai.vercel.app
```

---

## ⚙️ Backend Deployment (Render)

### Step 1: Create Flask API Service

1. Visit https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:

**Name:** `codescan-api`

**Environment:** `Python 3.10`

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn --worker-class eventlet -w 1 run:app
```

**Root Directory:**
```
backend
```

### Step 2: Add Environment Variables

In Render Service Settings → Environment, add:

```env
# Flask Config
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here

# Database
DATABASE_URL=sqlite:////var/data/codescan.db

# AI Provider Keys
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
HUGGING_FACE_API_KEY=your_huggingface_token

# Redis (will be added separately)
REDIS_URL=redis://default:password@redis-instance.onrender.com:6379
CELERY_BROKER_URL=redis://default:password@redis-instance.onrender.com:6379/0
CELERY_RESULT_BACKEND=redis://default:password@redis-instance.onrender.com:6379/1

# CORS Settings
FRONTEND_URL=https://codescan-ai.vercel.app
CORS_ORIGINS=https://codescan-ai.vercel.app,http://localhost:5173

# JWT Config
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=900
JWT_REFRESH_TOKEN_EXPIRES=604800
```

### Step 3: Add Persistent Volume

1. In Render dashboard, go to Service Settings
2. Add a **Disk** volume:
   - **Name:** `data`
   - **Mount Path:** `/var/data`
   - **Size:** 1 GB (or more for production)

This ensures your SQLite database persists across deployments.

### Step 4: Add Redis Add-on

1. In Render dashboard, click "Add-ons"
2. Create a Redis instance:
   - **Name:** `codescan-redis`
   - **Plan:** Free (or paid for production)
3. Copy the Redis URL to `REDIS_URL` environment variable

### Step 5: Deploy

Render will auto-deploy on every push. Your API will be available at:
```
https://codescan-api.onrender.com
```

---

## 🔄 Celery Worker Service (Background Tasks)

### Create Celery Worker Service

1. In Render, create a new **Background Worker**
2. Configure:

**Name:** `codescan-worker`

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
celery -A celery_worker.celery worker --loglevel=info --concurrency=2
```

**Environment Variables:** (Same as Flask API service)

### Connect to Redis

The worker will automatically connect to the Redis instance using the `REDIS_URL` environment variable.

---

## 🗄️ Database Setup

### SQLite (Development/Small Scale)

Already included. No additional setup needed.

### PostgreSQL (Enterprise/Production Scale)

For larger deployments, migrate to PostgreSQL:

1. In Render, add PostgreSQL Add-on
2. Update `DATABASE_URL` environment variable
3. Run migrations:

```bash
flask db upgrade
```

---

## 🔒 SSL/HTTPS

Both Vercel and Render provide automatic SSL certificates. HTTPS is enabled by default.

---

## 📨 Email Notifications (Optional)

To enable email notifications for scan results:

1. Set up SendGrid integration in Render
2. Add to environment variables:

```env
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@codescan-ai.com
```

---

## 🔐 Security Checklist

Before going to production:

- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Enable HTTPS (automatic on Vercel/Render)
- [ ] Configure CORS to allow only your frontend domain
- [ ] Set up API rate limiting
- [ ] Rotate API keys regularly
- [ ] Set up monitoring and alerts
- [ ] Enable database backups
- [ ] Use environment variables for all secrets
- [ ] Set up error logging (Sentry/LogRocket)

---

## 📊 Monitoring & Logging

### Render Logs

View logs in Render dashboard:
```
Service → Logs
```

### Error Tracking (Optional)

Integrate Sentry for error tracking:

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your_sentry_dsn",
    integrations=[FlaskIntegration()],
    traces_sample_rate=0.1
)
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        run: |
          npm install -g vercel
          vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        run: |
          curl https://api.render.com/deploy/srv-${{ secrets.RENDER_API_ID }}
```

---

## 🐛 Troubleshooting

### API Not Starting

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Database Connection Error

**Error:** `sqlite3.OperationalError: unable to open database file`

**Solution:** Ensure `/var/data` volume is mounted and writable

### Redis Connection Timeout

**Error:** `redis.exceptions.ConnectionError`

**Solution:** Verify Redis URL in environment variables and network connectivity

### Socket.IO Connection Issues

**Error:** WebSocket connection fails

**Solution:**
1. Ensure `FRONTEND_URL` is correctly set
2. Check CORS configuration
3. Verify WebSocket is enabled in Render (default: enabled)

---

## 📈 Scaling

### Horizontal Scaling (Multiple Instances)

For production load, use Render's auto-scaling:

**In Render Service Settings:**
- Enable "Auto-Deploy"
- Set instance count to 2-3
- Configure load balancer (included)

### Upgrade Database

**Migrate SQLite → PostgreSQL:**

```bash
# Export data
sqlite3 codescan.db .dump > backup.sql

# Create PostgreSQL instance on Render
# Update DATABASE_URL
# Run migrations
flask db upgrade
```

---

## 💰 Cost Estimation

| Component | Free Tier | Pro Tier | Notes |
|-----------|-----------|----------|-------|
| **Vercel Frontend** | 100 GB bandwidth/month | $20/month | Includes SSL, CDN |
| **Render API** | $7/month | $12+/month | Auto-scales, includes SSL |
| **Render Redis** | Free | $5+/month | Managed Redis |
| **Render PostgreSQL** | N/A | $15+/month | For scaling |
| **Celery Worker** | $7/month | $12+/month | Background jobs |

**Total Estimated Cost:** $7-40/month depending on scale

---

## 📞 Support

- **Vercel Support:** https://vercel.com/support
- **Render Support:** https://render.com/docs
- **CodeScan AI Issues:** https://github.com/pauldev-hub/CodeScan-AI/issues

---

## 🔄 Updates & Maintenance

### Zero-Downtime Deployments

Both Vercel and Render support zero-downtime deployments:

1. New version is deployed to a canary instance
2. Health checks pass
3. Traffic gradually shifts to new version
4. Old version is terminated

### Rollback

If deployment fails:

**Vercel:** Go to Deployments, select previous version, click "Make Production"

**Render:** Go to Deploys, select previous deployment, click "Deploy"

---

## ✅ Post-Deployment Checklist

- [ ] Frontend loads at custom domain
- [ ] API responds to health checks
- [ ] Authentication works
- [ ] Scans complete successfully
- [ ] Results export (PDF, JSON, CSV)
- [ ] Real-time chat works
- [ ] Error logging is active
- [ ] Backups are scheduled
- [ ] Monitoring/alerts are set up
- [ ] Performance is within SLA
