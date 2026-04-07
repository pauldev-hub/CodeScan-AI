# 🏗️ CodeScan AI - Technical Architecture

## System Overview

CodeScan AI is a distributed system composed of three main layers:

1. **Frontend Layer** (React + Vite) - User interface
2. **API Layer** (Flask) - Business logic & REST endpoints
3. **Background Layer** (Celery) - Async processing

---

## 🏢 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│          CLIENT LAYER (Browser)                     │
│  React SPA + Vite + Tailwind CSS + Socket.IO        │
└──────────────────┬──────────────────────────────────┘
                   │ HTTPS/WebSocket
┌──────────────────▼──────────────────────────────────┐
│           API GATEWAY (Render)                      │
│  Gunicorn + Flask + Flask-SocketIO                  │
└──────────────┬─────────────────────────────────────┘
               │
      ┌────────┼────────┬──────────────┐
      │        │        │              │
┌─────▼──┐ ┌───▼────┐ ┌─▼──────────┐ ┌──▼──────────┐
│ SQLite │ │ Redis  │ │ Celery     │ │ File Storage│
│ (Data) │ │(Cache) │ │ (Queue)    │ │(Temp Files) │
└────────┘ └────────┘ └────────────┘ └─────────────┘
      │        │           │
      └────────┴───────────┘
         │
    └────▼────────────────────────────────┐
    │   External Services                 │
    │  - Groq API (Primary AI)            │
    │  - Gemini API (Fallback)            │
    │  - Llama (Fallback)                 │
    │  - GitHub API                       │
    └─────────────────────────────────────┘
```

---

## 📊 Database Schema

### Core Tables

#### users
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- Bcrypt hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_username ON users(username);
```

#### scans
```sql
CREATE TABLE scans (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    source_type VARCHAR(50),  -- 'paste', 'upload', 'github', 'api'
    filename VARCHAR(255),
    language VARCHAR(50),
    code_hash VARCHAR(64),  -- SHA256 for deduplication
    status VARCHAR(50),  -- 'queued', 'processing', 'completed', 'failed'
    health_score INTEGER,  -- 0-100 rating
    total_findings INTEGER,
    critical_count INTEGER,
    high_count INTEGER,
    medium_count INTEGER,
    low_count INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_id ON scans(user_id);
CREATE INDEX idx_status ON scans(status);
CREATE INDEX idx_created_at ON scans(created_at);
CREATE INDEX idx_code_hash ON scans(code_hash);
```

#### findings
```sql
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    type VARCHAR(100),  -- 'SQL Injection', 'XSS', 'Authentication', etc.
    severity VARCHAR(20),  -- 'critical', 'high', 'medium', 'low'
    file TEXT,
    line_number INTEGER,
    column_number INTEGER,
    description TEXT,
    code_snippet TEXT,
    recommendation TEXT,
    cve_reference VARCHAR(50),  -- Optional CVE/CWE reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scan_id ON findings(scan_id);
CREATE INDEX idx_severity ON findings(severity);
```

#### reports
```sql
CREATE TABLE reports (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL UNIQUE REFERENCES scans(id),
    title VARCHAR(255),
    summary TEXT,
    shared_token VARCHAR(100) UNIQUE,
    share_expires_at TIMESTAMP,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shared_token ON reports(shared_token);
```

#### comments
```sql
CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    status VARCHAR(50),  -- 'acknowledged', 'fixed', 'dismissed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_report_id ON comments(report_id);
CREATE INDEX idx_finding_id ON comments(finding_id);
```

---

## 🔄 Request Flow

### Code Scanning Flow

```
1. User Action (Frontend)
   ↓
2. POST /api/scan/submit
   ├─ Validate input
   ├─ Create scan record (status: queued)
   ├─ Queue Celery task
   └─ Return scan_id (202 Accepted)
   ↓
3. Celery Task
   ├─ Update scan status (processing)
   ├─ Download/Read code
   ├─ Call AI Provider (Groq → Gemini → Llama)
   ├─ Parse AI response
   ├─ Store findings in database
   ├─ Calculate health score
   └─ Update scan status (completed)
   ↓
4. Frontend Polling (GET /api/scan/status)
   └─ User sees results when ready
   ↓
5. User Action (View Results)
   └─ GET /api/scan/results/:scan_id
```

### Real-Time Chat Flow

```
1. User connects to Socket.IO
   ├─ Authenticate JWT
   ├─ Join scan-specific room
   └─ Connection established
   ↓
2. User sends message
   ├─ Emit: chat:send_message
   ├─ Include scan context
   └─ Include previous findings
   ↓
3. Backend processing
   ├─ Validate user has access to scan
   ├─ Format context for AI
   ├─ Call AI Provider with context
   └─ Stream response
   ↓
4. Client receives response
   ├─ Receive: chat:ai_response
   ├─ Update UI
   └─ Show formatted response
```

---

## 🤖 AI Provider System

### Provider Selection Logic

```python
def analyze_code(code: str) -> dict:
    providers = [
        ('groq', analyze_with_groq),
        ('gemini', analyze_with_gemini),
        ('llama', analyze_with_llama),
    ]
    
    for provider_name, analyze_fn in providers:
        try:
            result = analyze_fn(code)
            log_provider_success(provider_name)
            return result
        except (Timeout, RateLimit) as e:
            log_provider_failure(provider_name, str(e))
            continue  # Try next provider
    
    raise Exception("All providers failed")
```

### Response Format

All providers must return:

```json
{
  "health_score": 62,
  "findings": [
    {
      "type": "SQL Injection",
      "severity": "critical",
      "line": 42,
      "description": "...",
      "recommendation": "..."
    }
  ],
  "summary": "Found 18 issues"
}
```

---

## 💾 Caching Strategy

### Redis Cache Keys

```
// Scan results (1 hour TTL)
scans:{scan_id}:results

// User scan history (30 minutes TTL)
users:{user_id}:scan_history

// API response cache (5 minutes TTL)
api:response:{endpoint}:{params_hash}

// Session tokens (lifetime = token expiry)
auth:tokens:{user_id}:{token}
```

### Cache Invalidation

```python
# On new scan creation
cache.delete(f'users:{user_id}:scan_history')

# On scan completion
cache.set(f'scans:{scan_id}:results', results, ttl=3600)

# On user logout
cache.delete(f'auth:tokens:{user_id}:*')
```

---

## 🔐 Authentication & Authorization

### JWT Token Structure

```
Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload:
{
  "user_id": "user_123",
  "username": "johndoe",
  "email": "john@example.com",
  "iat": 1680881400,
  "exp": 1680885000,  // 1 hour
  "type": "access"
}

Signature: HMACSHA256(base64UrlEncode(header) + "." + base64UrlEncode(payload), secret)
```

### Refresh Token Rotation

```
Access Token: Valid for 15 minutes
Refresh Token: Valid for 7 days

On /auth/refresh:
1. Validate refresh token
2. Issue new access token
3. Issue new refresh token
4. Invalidate old refresh token in Redis
```

---

## 🚀 Celery Task Architecture

### Task Queues

| Queue | Priority | Tasks |
|-------|----------|-------|
| `high` | 1 | Real-time chat responses, urgent scans |
| `default` | 5 | Normal code scans |
| `low` | 10 | Report generation, cleanup tasks |

### Task Definition

```python
@celery.task(queue='default', max_retries=3)
def scan_code_task(scan_id: str):
    """
    Main code scanning task.
    
    Retry logic:
    - Retry 1: After 5 seconds
    - Retry 2: After 30 seconds
    - Retry 3: After 2 minutes
    """
    try:
        scan = Scan.query.get(scan_id)
        scan.update_status('processing')
        
        findings = analyze_code(scan.code)
        scan.store_findings(findings)
        
        scan.update_status('completed')
    except Exception as e:
        # Exponential backoff retry
        raise scan_code_task.retry(exc=e, countdown=2 ** self.request.retries)
```

---

## 📈 Performance Optimizations

### Frontend

- **Code Splitting**: Route-based splitting with lazy loading
- **Image Optimization**: WebP format, lazy loading
- **Caching**: Service Worker for offline support
- **Bundle Size**: Tree-shaking, minification

### Backend

- **Database Indexing**: Indexed frequently queried columns
- **Query Optimization**: Eager loading with SQLAlchemy joinedload
- **Result Caching**: Redis cache for common queries
- **Async Processing**: Long operations moved to Celery

### Network

- **Compression**: Gzip for responses > 1KB
- **CDN**: Vercel's global CDN for static assets
- **WebSocket**: Persistent connection for real-time chat

---

## 🔍 Monitoring & Metrics

### Key Metrics

| Metric | Target | Alert |
|--------|--------|-------|
| API Response Time | < 200ms | > 500ms |
| Celery Task Success Rate | > 99% | < 95% |
| Database Query Time | < 50ms | > 200ms |
| Error Rate | < 0.1% | > 1% |
| Memory Usage | < 80% | > 90% |

### Logging

```python
# Application logs
app.logger.info(f"Scan {scan_id} completed")

# Error tracking
sentry.capture_exception(e)

# Performance metrics
statsd.timing('scan.completion_time', duration_ms)
```

---

## 🛡️ Security Considerations

### Input Validation

```python
# File upload validation
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_LANGUAGES = ['python', 'javascript', 'java', ...]

# Code injection prevention
# - Use parameterized queries
# - Sanitize all user inputs
# - Validate file extensions
```

### Rate Limiting

```
# Per user, per hour
GET /api/scan/results: 100 requests
POST /api/scan/submit: 10 scans
POST /api/auth/login: 5 attempts
```

### API Key Rotation

```bash
# Generate new keys
# Update environment variables
# Restart services
# Remove old keys
```

---

## 🔄 Deployment Architecture

### Development
- Local SQLite database
- Local Redis (optional)
- Direct Python execution

### Staging
- PostgreSQL database
- Managed Redis
- Multiple Celery workers
- Health checks enabled

### Production
- PostgreSQL with replication
- Redis cluster
- Multiple API instances
- Multiple Celery workers
- Monitoring & alerting

---

## 📊 Scalability

### Horizontal Scaling

```
Load Balancer
├─ API Instance 1
├─ API Instance 2
├─ API Instance 3
└─ API Instance N

Celery Workers
├─ Worker 1
├─ Worker 2
├─ Worker 3
└─ Worker N
```

### Database Scaling

- **Read Replicas**: For scaling read-heavy workloads
- **Sharding**: Future enhancement for massive scale
- **Archival**: Move old scans to cold storage

---

## 🔗 External Service Integration

### GitHub API

```python
# Authentication
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Fetch repository
GET /repos/{owner}/{repo}/contents/{path}
```

### AI Providers

All providers use request timeout of **30 seconds** with exponential backoff:
- Attempt 1: 0s delay
- Attempt 2: 2s delay
- Attempt 3: 4s delay

---

## 📝 Future Architecture

### Planned Enhancements

- **Machine Learning**: ML-based vulnerability classification
- **Custom Rules Engine**: Allow organizations to define custom rules
- **Multi-Tenancy**: Support for enterprise customers
- **GraphQL API**: Supplement REST API
- **Webhooks**: Integration with CI/CD systems
- **Mobile Apps**: Native iOS/Android apps

---

## 🔄 Development Workflow

### Local Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_ENV=development
flask run

# Frontend
cd frontend
npm install
npm run dev

# Celery (optional)
celery -A app.tasks.scan_tasks worker --loglevel=debug
```

### Testing

```bash
# Backend tests
pytest --cov=app

# Frontend tests
npm run test

# Integration tests
pytest tests/integration/
```
