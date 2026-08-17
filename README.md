# Fraud Shield AI

**FraudGPT vs ShieldGPT** — An adversarial fraud detection platform with real ML scoring, JWT auth, per-user data isolation, and an admin dashboard.

---

## Quick Start

### Prerequisites
- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **MongoDB 7+** running on `localhost:27017` (or via Docker)

### 1. Clone & Install

```bash
git clone https://github.com/adritanotadorito/fraud-simulator.git
cd fraud-simulator

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env     # Edit JWT_SECRET for production!
cd ..

# Frontend
cd fraud-dashboard
npm install
cp .env.example .env
cd ..
```

### 2. Train ML Models (first time only)

```bash
cd ml
python retrain_models.py
cd ..
```

This generates `ml/models/fraud_model.pkl` (XGBoost) and `ml/models/isolation_forest.pkl` using 9 derivable features — no Kaggle PCA columns needed.

### 3. Run

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd fraud-dashboard
npm run dev
```

Open **http://localhost:5173** — sign up to create your account.

### Docker (alternative)

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

---

## Architecture

```
fraud-simulator/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── auth/            # JWT + bcrypt auth (security.py, dependencies.py)
│   │   ├── ml/              # XGBoost + IsolationForest scorers (9-feature)
│   │   ├── orchestrator/    # ShieldGPT orchestrator (7 engines + fusion)
│   │   ├── routers/         # API routes (transactions, auth, admin, fraud, etc.)
│   │   └── models/          # Pydantic schemas
│   └── requirements.txt
├── fraud-dashboard/         # Vite + React + TailwindCSS v4 frontend
│   ├── src/
│   │   ├── context/         # AuthContext, WebSocketContext
│   │   ├── pages/           # UserDashboard, AdminDashboard, Login, Signup, ops pages
│   │   └── components/      # Navbar, ProtectedRoute, etc.
│   └── package.json
├── ml/
│   ├── models/              # Trained .pkl files (git-tracked)
│   └── retrain_models.py    # Retraining script
└── docker-compose.yml
```

## Auth System

- **First signup = admin** (bootstrap rule). Every subsequent signup = regular user.
- JWT tokens (HS256, 8-hour expiry) stored in `localStorage`.
- Admin can promote/demote users via Admin Dashboard.

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/signup` | POST | - | Register (first = admin) |
| `/api/auth/login` | POST | - | Login, get JWT |
| `/api/auth/me` | GET | Bearer | Current user profile |
| `/api/transactions/upload-file` | POST | Bearer | Upload CSV/JSON |
| `/api/transactions/score-uploaded` | POST | Bearer | Score uploaded dataset |
| `/api/transactions/my-uploads` | GET | Bearer | User's upload history |
| `/api/admin/users` | GET | Admin | All users |
| `/api/admin/stats` | GET | Admin | Platform stats |

## ML Pipeline

Models are trained on **9 derivable features** (not Kaggle PCA):

| Feature | Description |
|---------|-------------|
| `amount` | Transaction amount |
| `amount_zscore` | Z-score relative to dataset mean |
| `transaction_velocity` | Rate of recent transactions |
| `time_diff` | Seconds since last transaction |
| `device_change_flag` | VPN/emulator/Tor detected |
| `geo_velocity` | Impossible travel speed (km/h) |
| `biometric_deviation` | Mouse/typing pattern deviation |
| `hour_of_day` | Transaction hour (0-23) |
| `is_new_merchant` | First time with this merchant |

The orchestrator runs 7 engines in parallel (XGBoost, IsolationForest, RuleEngine, GraphAnalysis, BiometricAnalysis, GeoAnalysis, ThreatIntel), fuses scores, and produces ALLOW/FLAG/BLOCK decisions.

## Environment Variables

```env
# Backend (.env in backend/)
FRAUD_SHIELD_MONGO_URI=mongodb://localhost:27017
FRAUD_SHIELD_JWT_SECRET=<generate with: openssl rand -hex 32>
FRAUD_SHIELD_JWT_EXPIRE_MINUTES=480
FRAUD_SHIELD_GEMINI_API_KEY=<optional>

# Frontend (.env in fraud-dashboard/)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/api/transactions/stream
```

## License

MIT