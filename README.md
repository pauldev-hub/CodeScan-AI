# 🔍 CodeScan AI

<!-- Badges Section -->
<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10+-3776ab?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-61dafb?logo=react&logoColor=white&style=for-the-badge)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/status-In-Development%20Dev-yellow?style=for-the-badge)](https://github.com)

[![Flask](https://img.shields.io/badge/flask-3.0+-000000?logo=flask&style=for-the-badge)](https://flask.palletsprojects.com/)
[![Vite](https://img.shields.io/badge/vite-5.0+-9400d3?logo=vite&logoColor=white&style=for-the-badge)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/sqlite-3.40+-003b57?logo=sqlite&logoColor=white&style=for-the-badge)](https://www.sqlite.org/)
[![Tailwind CSS](https://img.shields.io/badge/tailwind%20css-3.3+-38b2ac?logo=tailwind-css&logoColor=white&style=for-the-badge)](https://tailwindcss.com/)

</div>

---

## 🎯 Introduction

**CodeScan AI** is an intelligent, AI-powered code analysis platform designed to help developers understand security vulnerabilities and code quality issues in plain English. Perfect for students, junior developers, and teams looking for a second opinion on code safety before shipping to production.

With real-time AI-powered code scanning, comprehensive vulnerability analysis, and an interactive chat interface, CodeScan AI transforms complex security findings into actionable insights.

---

## 📚 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [✨ Key Features](#-key-features)
- [🌊 Why CodeScan AI in the Era of Vibecoding?](#-why-codescan-ai-in-the-era-of-vibecoding)
- [🏗️ Architecture Overview](#️-architecture-overview)
- [📖 Usage Examples](#-usage-examples)
- [🔐 Security & Privacy](#-security--privacy)
- [📋 Known Limitations & Roadmap](#-known-limitations--roadmap)
- [📁 Project Structure](#-project-structure)
- [🔌 API Endpoints](#-api-endpoints)
- [🧪 Testing](#-testing)
- [🚀 Deployment](#-deployment)
- [🤖 AI Provider System](#-ai-provider-system)
- [📊 Database Schema](#-database-schema)
- [🔧 Development Workflow](#-development-workflow)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [📬 Support & Feedback](#-support--feedback)
- [🙏 Acknowledgments](#-acknowledgments)
- [🌟 Built by Pratyush](#-independently-designed--built-by-pratyush)

---

## ✨ Key Features

<table>
<tr>
<td>

### 🛡️ **Security Analysis**
- Detects OWASP vulnerabilities
- Identifies SQL injection risks
- Spots authentication issues
- Finds hardcoded secrets

</td>
<td>

### 🤖 **AI-Powered Insights**
- Multi-provider AI fallback system
- Plain English explanations
- Real-time chat with AI
- Context-aware recommendations

</td>
</tr>
<tr>
<td>

### 📊 **Rich Visualizations**
- Severity pie charts
- Health score timeline
- Scan history comparison
- Issue breakdown by category

</td>
<td>

### 📤 **Export Options**
- PDF reports with charts
- JSON exports
- CSV downloads
- Markdown formatting

</td>
</tr>
<tr>
<td>

### 🚀 **Multiple Input Methods**
- Paste code directly
- Upload files
- GitHub repository integration
- Batch scanning

</td>
<td>

### 👥 **Collaboration**
- Share reports publicly
- Comment on findings
- Team collaboration tools
- Scan history tracking

</td><td>

### 🎓 **Beginner Mode** ⭐ (Differentiator)
- Non-jargon explanations for complex vulnerabilities
- Step-by-step guidance on fixing issues
- Best practice recommendations
- Interactive learning resources

</td></tr>
</table>

---

## � **Why CodeScan AI in the Era of Vibecoding?**

<div align="center">

### The Problem
In today's fast-paced development culture ("vibecoding"), developers often:
- Rush to ship features without thorough code review
- Lack expertise to spot security vulnerabilities
- Need a "second opinion" but lack access to experienced reviewers
- Struggle to bridge the gap between non-technical stakeholders and technical implementation

### The Solution: CodeScan AI

**For Non-Technical Coders & Product Managers:**
- 📖 **Plain English Explanations** — No jargon, just clear insights
- 🎓 **Educational Approach** — Learn about code quality as you go
- 🤔 **Ask Questions** — Interactive AI chat explains every finding
- 📊 **Visual Reports** — Understand issues through beautiful charts and breakdowns
- ✅ **Approval Ready** — Get the confidence to review code deliverables

**For Technical Coders & Architects:**
- 🛡️ **Deep Security Analysis** — OWASP vulnerabilities, injection attacks, auth issues
- ⚡ **Instant Feedback Loop** — Review code in seconds, not hours
- 🔄 **Integration Ready** — CI/CD friendly, GitHub integration, API-first
- 📈 **Track Improvements** — Timeline charts and historical data
- 💬 **Collaborative Review** — Share findings with teams, add comments

### The Impact
```
Traditional Code Review    →    CodeScan AI Review
─────────────────────────────────────────────────────
⏱️  Takes hours/days          ⚡ Takes seconds
👥 Requires senior devs      🤖 AI-powered analysis
❌ Misses edge cases         ✅ Catches known patterns
😴 Creates bottlenecks       🚀 Accelerates delivery
💭 Hard to learn from        📚 Educational feedback
```

### Perfect For
- 🎓 **Students & Bootcamp Graduates** — Learn best practices while building
- 👶 **Junior Developers** — Get instant mentorship on code quality
- 🏃 **Startup Teams** — Move fast without sacrificing security
- 🏢 **Enterprise Teams** — Standardize code review across projects
- 🌐 **Open Source Maintainers** — Scale your review process

</div>

---

## �🏗️ Architecture Overview

### Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Vercel)                       │
│  React 18 + Vite + Tailwind CSS + Recharts + Socket.IO      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                    API LAYER (Render)                        │
│       Flask + Flask-SocketIO + JWT Authentication           │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼────┐  ┌──────▼──────┐  ┌───▼──────────┐
│  Database  │  │ Celery Task │  │ Redis Cache  │
│  (SQLite)  │  │   Queue     │  │  & Broker    │
└────────────┘  └─────────────┘  └──────────────┘
        │
        └────────────────────┐
                             │
                ┌────────────▼─────────────┐
                │  AI Provider Fallback    │
                │  - Groq (Primary)        │
                │  - Gemini (Fallback 1)   │
                │  - Llama (Fallback 2)    │
                └──────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React + Vite | Lightning-fast SPA with hot reload |
| **Backend API** | Flask + Gunicorn | REST API with real-time WebSocket support |
| **Database** | SQLite + SQLAlchemy | Persistent data storage with ORM |
| **Task Queue** | Celery + Redis | Async scan processing & caching |
| **AI Integration** | Multi-provider | Groq → Gemini → Llama with automatic fallback |
| **Authentication** | JWT + Bcrypt | Stateless auth with token refresh |
| **Real-time Chat** | Socket.IO | Bidirectional AI chat communication |

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.10+ 
- **Node.js** 16+ & **npm** 8+
- **Git** 2.30+

### Installation

#### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/codescan-ai.git
cd codescan-ai
```

#### 2️⃣ Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv

.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Initialize database
flask db upgrade

# Run the backend server
python run.py
```

Backend will be available at `http://localhost:5000`

#### 3️⃣ Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Configure API endpoint (default: http://localhost:5000)

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

#### 4️⃣ (Optional) Celery Worker for Background Tasks
```bash
cd backend

# In a new terminal (with activated venv):
celery -A app.tasks.scan_tasks worker --loglevel=info
```

---

## 📖 Usage Examples

### 🔍 Scanning Code

**Option 1: Paste Code**
1. Navigate to the Scanner page
2. Select "Paste Code"
3. Paste your code and select the language
4. Click "Scan"

**Option 2: Upload File**
1. Select "Upload File"
2. Choose a single file or multiple files
3. Click "Scan"

**Option 3: GitHub Repository**
1. Select "GitHub Repository"
2. Enter repository URL (e.g., `https://github.com/user/repo`)
3. Click "Analyze"

### 💬 Interactive Chat

After a scan completes:
- Ask the AI questions about vulnerabilities
- Request fix suggestions
- Get explanations in plain English
- Request best practices

### 📊 Viewing Results

Results include:
- **Health Score**: 0-100 rating
- **Severity Breakdown**: Critical, High, Medium, Low issues
- **Timeline**: Track improvements over time
- **Detailed Issues**: Click any issue for full explanation
- **Export Options**: Download as PDF, JSON, or CSV

---

## 🔐 Security & Privacy

### Authentication
- **Password Security**: Bcrypt hashing with cost factor 12
- **Token System**: 15-minute access tokens + 7-day refresh tokens
- **Automatic Refresh**: Tokens auto-refresh via Axios interceptors

### Data Privacy
- **No Data Storage**: Uploaded code is processed temporarily, never permanently stored
- **API Key Protection**: All API keys stored as environment variables
- **Encrypted Transmission**: HTTPS enforced in production

### Source Code Analysis
- Pattern-based vulnerability detection
- OWASP Top 10 compliance
- Zero external data transfer for scanning
- Local result caching with Redis

---

## � Known Limitations & Roadmap

### Current Limitations (v1.0)
- **Rate Limiting**: 10 scans/hour per user (free tier) to prevent abuse
- **Database Scale**: SQLite is suitable for small to medium deployments; enterprise deployments should migrate to PostgreSQL
- **File Size Limit**: Maximum 5MB per file upload
- **Language Support**: Currently supports Python, JavaScript, Java, Go, Rust (expanding in v1.1)
- **Async Processing**: Large repositories (>10K files) require Celery worker for non-blocking analysis

### Planned for v1.1 (Q2 2026)
- 🔄 **Batch Scanning**: Upload multiple files simultaneously
- 📦 **Docker Support**: Docker Compose setup for one-click local deployment
- 🔗 **CI/CD Integration**: GitHub Actions, GitLab CI, Jenkins plugins
- 🌍 **Multi-Language Support**: Add C/C++, TypeScript, PHP, Ruby
- 📈 **Advanced Analytics**: Trend analysis, team metrics, vulnerability timeline
- 🔐 **Enterprise Auth**: SAML2, OAuth2, LDAP support
- 💾 **PostgreSQL Support**: Better scalability for production

### Future Roadmap (v1.2+)
- Machine learning-based false positive reduction
- Custom rule engine for organization policies
- IDE plugins (VS Code, JetBrains)
- Mobile app for report viewing
- On-premise deployment guide

---

## �📁 Project Structure

```
codescan-ai/
├── frontend/                    # React + Vite SPA
│   ├── src/
│   │   ├── components/         # UI Components (Auth, Scanner, Results, Chat, etc.)
│   │   ├── pages/             # Page routes
│   │   ├── services/          # API & Socket.IO services
│   │   ├── hooks/             # Custom React hooks (useAuth, useTheme, useAIChat)
│   │   ├── context/           # React Context (Auth, Theme)
│   │   └── utils/             # Utilities (formatters, validators, storage)
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── backend/                     # Flask + Python
│   ├── app/
│   │   ├── models/            # SQLAlchemy ORM models (User, Scan, Report)
│   │   ├── routes/            # API endpoints (auth, scan, report, export)
│   │   ├── services/          # Business logic (AI, GitHub, Export, etc.)
│   │   ├── sockets/           # Socket.IO event handlers (chat)
│   │   ├── tasks/             # Celery async tasks
│   │   └── utils/             # Helpers (validators, formatters, security)
│   ├── tests/                 # Pytest test suite
│   ├── migrations/            # Alembic DB migrations
│   ├── requirements.txt
│   ├── run.py                # Flask entry point
│   └── celery_worker.py      # Celery worker entry point
│
└── docs/                        # Documentation
    ├── API.md                 # REST API reference
    ├── DEPLOYMENT.md          # Vercel + Render setup
    └── ARCHITECTURE.md        # System design details
```

---

## 🔌 API Endpoints

### Authentication
```
POST   /api/auth/register       Register new user
POST   /api/auth/login          User login
POST   /api/auth/refresh        Refresh access token
POST   /api/auth/logout         User logout
```

### Scanning
```
POST   /api/scan/submit         Submit code for scanning
GET    /api/scan/status/:id     Check scan progress
GET    /api/scan/results/:id    Get scan results
GET    /api/scan/history        Get user's scan history
```

### Reports & Sharing
```
GET    /api/report/:id          Get scan report
POST   /api/report/:id/share    Generate shareable link
GET    /api/report/:id/shared   View shared report
POST   /api/report/:id/comment  Add comment to report
```

### Export
```
GET    /api/export/:id/pdf      Export as PDF
GET    /api/export/:id/json     Export as JSON
GET    /api/export/:id/csv      Export as CSV
```

---

## 🧪 Testing

### Run All Tests
```bash
cd backend
pytest
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test Suite
```bash
pytest tests/test_auth.py -v
pytest tests/test_scan_routes.py -v
```

### Frontend Tests
```bash
cd frontend
npm run test
```

---

## 🚀 Deployment

### Frontend (Vercel)
```bash
cd frontend
npm run build
# Deploy to Vercel (connected via GitHub)
```

### Backend (Render)
1. Create two Render services:
   - **Flask API**: `python run.py` (gunicorn + eventlet)
   - **Celery Worker**: `celery -A app.tasks.scan_tasks worker`

2. Configure environment variables in Render dashboard

3. Add managed Redis instance

4. Link SQLite database volume for persistence

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed setup.

---

## 🤖 AI Provider System

CodeScan AI uses an intelligent fallback system for AI analysis:

```
Request → Groq (Primary)
            ↓
         [Timeout/Error]
            ↓
         Gemini (Fallback 1)
            ↓
         [Timeout/Error]
            ↓
         Llama via HuggingFace (Fallback 2)
            ↓
         Result or Error
```

**Supported Providers:**
- 🚀 **Groq**: Fast, free tier, recommended
- 🔥 **Google Gemini**: Fast, free tier, large context
- 🦙 **Llama**: Open-source, free, community-supported

**Configuration:** Set provider API keys in `.env`:
```env
GROQ_API_KEY=your_groq_key
GOOGLE_GEMINI_API_KEY=your_gemini_key
HUGGINGFACE_API_KEY=your_hf_key
```

---

## 📊 Database Schema

### Key Tables
- **users**: User accounts with hashed passwords
- **scans**: Code scan submissions with ID, status, health score
- **findings**: Individual vulnerabilities detected per scan
- **reports**: Shareable scan reports with metadata
- **comments**: Comments on findings for collaboration

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete schema.

---

## 🔧 Development Workflow

### Git Flow
```bash
# Create feature branch
git checkout -b feature/your-feature

# Commit with conventional commits
git commit -m "feat: add new feature"

# Push and open PR
git push origin feature/your-feature
```

### Code Quality
- **Backend**: Follows PEP 8 via `flake8` & `black`
- **Frontend**: ESLint + Prettier configured

### Running Locally
```bash
# Terminal 1: Backend (port 5000)
cd backend && python run.py

# Terminal 2: Celery Worker
cd backend && celery -A app.tasks.scan_tasks worker --loglevel=info

# Terminal 3: Frontend (port 5173)
cd frontend && npm run dev
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Contribution Guidelines
- Follow code style conventions (backend: PEP 8, frontend: ESLint)
- Write tests for new features
- Update documentation if needed
- Keep PRs focused and descriptive

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 📬 Support & Feedback

- 📧 **Email**: paulpratyush2@gmail.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/codescan-ai/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/codescan-ai/discussions)
- 📖 **Docs**: [Full Documentation](docs/)

---

## 🙏 Acknowledgments

- **Groq**, **Google**, and **Meta** for providing AI inference APIs
- **Flask**, **React**, and **Tailwind** communities
- All contributors and community members

---

---

## 🚀 **An Independent Project Designed & Built by Pratyush Paul**

<div align="center">

### ✨ **A Vision for Smarter Code Review in the Modern Era**

**CodeScan AI** is built by **Pratyush** — a developer who believes everyone deserves to understand the risks in their code, whether you've been coding for years or just shipped your first AI-assisted app.

This project was crafted from scratch with meticulous attention to:
- 🧠 **Deep-thought architecture** combining industry best practices
- 💡 **Innovation-focused** AI integration and user experience
- 🔧 **Production-ready** code with comprehensive testing
- 🎯 **Accessibility** making complex security findings understandable to all


---

### 🌟 **Built with ❤️ by Pratyush** 🌟

⭐ **If you find this project useful, please star it on GitHub!**

[GitHub](https://github.com/yourusername/codescan-ai) • [Try Online](#) • [Docs](docs/)

**Status**: 🟢 Active Development | **Latest**: v1.0.0

</div>
