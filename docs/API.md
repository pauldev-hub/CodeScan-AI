# 🔌 CodeScan AI - REST API Documentation

## Base URL

```
Production: https://api.codescan-ai.com
Development: http://localhost:5000
```

## Authentication

All endpoints (except `/auth/*` and `/`) require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Token Refresh

Access tokens expire after 15 minutes. Use the refresh token endpoint to obtain a new access token:

```bash
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token"
}
```

---

## 🔐 Authentication Endpoints

### Register User

**Endpoint:** `POST /api/auth/register`

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (201):**
```json
{
  "id": "user_123",
  "username": "johndoe",
  "email": "john@example.com",
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc..."
}
```

**Error Responses:**
- `400 Bad Request` - Invalid input or duplicate email
- `422 Unprocessable Entity` - Validation error

---

### Login User

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "id": "user_123",
  "username": "johndoe",
  "email": "john@example.com",
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc..."
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid email or password
- `404 Not Found` - User not found

---

### Refresh Token

**Endpoint:** `POST /api/auth/refresh`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc..."
}
```

---

### Logout User

**Endpoint:** `POST /api/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "message": "Logout successful"
}
```

---

## 📊 Scanning Endpoints

### Submit Code for Scanning

**Endpoint:** `POST /api/scan/submit`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "code": "def vulnerable_function():\n    user_input = input()\n    eval(user_input)",
  "language": "python",
  "filename": "app.py"
}
```

**OR for GitHub Repository:**
```json
{
  "github_url": "https://github.com/user/repo",
  "branch": "main"
}
```

**Response (202 Accepted):**
```json
{
  "scan_id": "scan_abc123",
  "status": "queued",
  "created_at": "2026-04-07T10:30:00Z",
  "message": "Scan queued for processing"
}
```

**Error Responses:**
- `400 Bad Request` - Missing required fields
- `413 Payload Too Large` - File exceeds 5MB limit
- `429 Too Many Requests` - Rate limit exceeded (10 scans/hour)

---

### Check Scan Status

**Endpoint:** `GET /api/scan/status/:scan_id`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "scan_id": "scan_abc123",
  "status": "processing",
  "progress": 45,
  "created_at": "2026-04-07T10:30:00Z",
  "started_at": "2026-04-07T10:31:00Z"
}
```

**Possible Status Values:**
- `queued` - Waiting to be processed
- `processing` - Currently being analyzed
- `completed` - Analysis complete, results available
- `failed` - Scan failed

---

### Get Scan Results

**Endpoint:** `GET /api/scan/results/:scan_id`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "scan_id": "scan_abc123",
  "status": "completed",
  "health_score": 62,
  "severity_breakdown": {
    "critical": 2,
    "high": 5,
    "medium": 8,
    "low": 3
  },
  "findings": [
    {
      "id": "finding_001",
      "type": "SQL Injection",
      "severity": "critical",
      "file": "app.py",
      "line": 42,
      "description": "User input passed directly to SQL query",
      "code_snippet": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
      "recommendation": "Use parameterized queries or ORM"
    }
  ],
  "created_at": "2026-04-07T10:30:00Z",
  "completed_at": "2026-04-07T10:35:00Z"
}
```

---

### Get Scan History

**Endpoint:** `GET /api/scan/history?limit=20&offset=0`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `limit` (optional, default: 20) - Number of scans to return
- `offset` (optional, default: 0) - Pagination offset

**Response (200):**
```json
{
  "scans": [
    {
      "scan_id": "scan_abc123",
      "filename": "app.py",
      "health_score": 62,
      "status": "completed",
      "created_at": "2026-04-07T10:30:00Z",
      "critical_count": 2,
      "high_count": 5
    }
  ],
  "total_count": 45,
  "limit": 20,
  "offset": 0
}
```

---

## 📋 Report Endpoints

### Get Scan Report

**Endpoint:** `GET /api/report/:scan_id`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "scan_id": "scan_abc123",
  "title": "Security Scan Report",
  "health_score": 62,
  "summary": "Found 18 security issues in the code",
  "findings": [...],
  "shared_token": null,
  "created_at": "2026-04-07T10:30:00Z",
  "user_id": "user_123"
}
```

---

### Generate Shareable Report Link

**Endpoint:** `POST /api/report/:scan_id/share`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (201):**
```json
{
  "scan_id": "scan_abc123",
  "shared_url": "https://codescan-ai.com/report/share/token_xyz789",
  "share_token": "token_xyz789",
  "expires_at": "2026-05-07T10:30:00Z"
}
```

---

### View Shared Report

**Endpoint:** `GET /api/report/:share_token/shared`

**Response (200):**
```json
{
  "scan_id": "scan_abc123",
  "title": "Security Scan Report",
  "health_score": 62,
  "findings": [...]
}
```

---

### Add Comment to Finding

**Endpoint:** `POST /api/report/:scan_id/comment`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "finding_id": "finding_001",
  "text": "This vulnerability was addressed in commit abc123",
  "status": "acknowledged"
}
```

**Response (201):**
```json
{
  "comment_id": "comment_def456",
  "finding_id": "finding_001",
  "text": "This vulnerability was addressed in commit abc123",
  "user_id": "user_123",
  "created_at": "2026-04-07T11:00:00Z"
}
```

---

## 📥 Export Endpoints

### Export as PDF

**Endpoint:** `GET /api/export/:scan_id/pdf`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** Binary PDF file

---

### Export as JSON

**Endpoint:** `GET /api/export/:scan_id/json`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "scan_id": "scan_abc123",
  "health_score": 62,
  "findings": [...],
  "exported_at": "2026-04-07T11:00:00Z"
}
```

---

### Export as CSV

**Endpoint:** `GET /api/export/:scan_id/csv`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** CSV format
```
finding_id,severity,type,file,line,description
finding_001,critical,SQL Injection,app.py,42,User input passed directly to SQL query
finding_002,high,Hardcoded Password,config.py,15,Database password hardcoded in source
```

---

## 🎯 Response Formats

### Success Response (2xx)

```json
{
  "data": {...},
  "status": "success",
  "message": "Operation completed successfully"
}
```

### Error Response (4xx, 5xx)

```json
{
  "error": "Invalid request",
  "status": "error",
  "code": "INVALID_INPUT",
  "details": "Email is required"
}
```

---

## 🔄 Rate Limiting

- **Free Tier**: 10 scans/hour per user
- **Pro Tier**: 100 scans/hour per user
- **Enterprise**: Unlimited scans

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1680881400
```

---

## 🧪 Testing with cURL

### Register
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Submit Scan
```bash
curl -X POST http://localhost:5000/api/scan/submit \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(input())",
    "language": "python",
    "filename": "script.py"
  }'
```

### Get Results
```bash
curl -X GET http://localhost:5000/api/scan/results/scan_abc123 \
  -H "Authorization: Bearer <access_token>"
```

---

## 📚 WebSocket Events (Real-time Chat)

**Connection Event:**
```javascript
socket.on('connect', () => {
  console.log('Connected to scan analysis AI chat');
});
```

**Send Message:**
```javascript
socket.emit('chat:send_message', {
  scan_id: 'scan_abc123',
  message: 'What does this vulnerability mean?'
});
```

**Receive Response:**
```javascript
socket.on('chat:ai_response', (data) => {
  console.log(data.response);
  // "This SQL injection vulnerability allows attackers..."
});
```

---

## 📖 API Versioning

Current API Version: **v1**

Future versions will be available at:
- `/api/v2/` (planned for Q2 2026)

---

## 📝 Changelog

### v1.0 (Current)
- Initial API release
- Authentication with JWT
- Code scanning (paste, upload, GitHub)
- Report generation and sharing
- Export to PDF, JSON, CSV
- Real-time chat with AI

### v1.1 (Planned)
- Batch scanning endpoint
- CI/CD integration webhooks
- Advanced filtering and search
- Team collaboration features
