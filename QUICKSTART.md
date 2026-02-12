# HHS Patient Portal - Quick Start Guide 🚀

## ✅ Setup Complete!

Both the Python API backend and Vue.js frontend are now connected and ready to use.

## 🏃 Running the Application

### Option 1: Run Both Servers (Recommended)

**Terminal 1 - Start the API Server:**
```bash
./run-api.sh
# or
npm run api
```

**Terminal 2 - Start the Frontend:**
```bash
npm run dev
```

### Option 2: Use the Background Script (Coming Soon)
```bash
./start-all.sh  # Starts both API and frontend
```

## 🌐 Access the Application

- **Frontend:** http://localhost:5173
- **API Server:** http://localhost:3000
- **API Health:** http://localhost:3000/health

## 🔑 Test Credentials

### Patient Account
- **Username:** `patient1`
- **Password:** `Patient123!`

### Doctor Account
- **Username:** `doctor1`
- **Password:** `Doctor123!`

## 📝 How to Use

1. **Login:**
   - Go to http://localhost:5173
   - Use one of the test credentials above
   - Click "Login"

2. **Patient Dashboard:**
   - View appointments
   - Request new appointments
   - View medical documents
   - Download documents

3. **Doctor Dashboard:**
   - View all appointments
   - Confirm pending appointments
   - Manage patient records

4. **Check-In:**
   - Click "Check In" button on login page
   - Enter patient name and birthday
   - Check in for today's appointment

## 🔧 Development Workflow

### Frontend Development
```bash
# Start Vite dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend API Development
```bash
# Activate virtual environment
source venv/bin/activate

# Start Flask server with hot reload
./run-api.sh

# Or manually
export PYTHONPATH=$(pwd)
python api/app.py
```

### Database Management
```bash
# Setup/reset database
./setup-db.sh

# Seed test users
python seed_users.py

# Connect to database
sudo -u postgres psql -d hhs_patient_portal

# View audit logs
sudo -u postgres psql -d hhs_patient_portal -c "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"
```

## 🔍 Testing the API Connection

### Using the Browser
1. Open http://localhost:5173
2. Open browser DevTools (F12)
3. Go to Network tab
4. Try to login
5. You should see requests to `http://localhost:3000/api/auth/login`

### Using curl
```bash
# Health check
curl http://localhost:3000/health

# Login
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"patient1","password":"Patient123!"}'

# Register new user
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newpatient",
    "email": "new@test.com",
    "password": "SecurePass123!",
    "firstName": "Jane",
    "lastName": "Doe",
    "dateOfBirth": "1995-03-20",
    "phone": "555-5678"
  }'
```

## 🛠️ Troubleshooting

### Frontend Not Connecting to API

**Check CORS:**
- API allows `http://localhost:5173` by default
- Check `.env` file: `ALLOWED_ORIGINS=http://localhost:5173`

**Check API is Running:**
```bash
curl http://localhost:3000/health
```

**Check Browser Console:**
- Open DevTools (F12)
- Look for CORS or network errors
- Verify API URL in requests

### Login Not Working

**Verify Test Users Exist:**
```bash
sudo -u postgres psql -d hhs_patient_portal -c "SELECT username, email, role FROM users;"
```

**Re-seed Database:**
```bash
python seed_users.py
```

**Check Audit Logs:**
```bash
sudo -u postgres psql -d hhs_patient_portal -c "SELECT user_id, action, details, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 5;"
```

### Database Connection Issues

**PostgreSQL Not Running:**
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

**Wrong Password:**
```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

## 📁 Project Structure

```
HHS-patient-portal/
├── api/                      # Python Flask API
│   ├── app.py               # Main Flask application
│   ├── db/                  # Database connection
│   ├── utils/               # Security, audit, sessions
│   ├── middleware/          # Auth middleware
│   └── routes/              # API routes
├── src/                     # Vue.js frontend
│   ├── api/                 # API client
│   ├── views/               # Vue components
│   ├── router/              # Vue router
│   └── store.ts             # State management
├── server/                  # Legacy TypeScript API (not used)
├── venv/                    # Python virtual environment
├── .env                     # Environment variables
├── run-api.sh              # Start API server
├── setup-db.sh             # Setup database
└── seed_users.py           # Create test users
```

## 🔐 Security Features Active

✅ **Password Hashing:** bcrypt with 12 rounds + pepper salt  
✅ **Session Management:** 15-minute auto-timeout  
✅ **Audit Logging:** All login attempts and data access tracked  
✅ **Rate Limiting:** 5 login attempts per 15 minutes  
✅ **Account Lockout:** After 5 failed attempts (30 minutes)  
✅ **CORS Protection:** Only allowed origins can access API  
✅ **HTTPS Ready:** SSL/TLS support in production  
✅ **SQL Injection Protection:** Parameterized queries  

## 📊 HIPAA Compliance

- All PHI access is logged with user ID, timestamp, IP, action
- Audit logs retained for 7 years (configurable)
- Sessions automatically expire after inactivity
- Password strength requirements enforced
- Account lockout prevents brute force attacks
- Background tasks clean up expired sessions and old logs

## 🎯 Next Steps

1. ✅ Both servers are running
2. ✅ Test users created
3. ✅ Frontend connected to API
4. 🔄 Test login functionality
5. 📝 Add more features as needed
6. 🚀 Deploy to production

## 📚 Documentation

- **Database Setup:** See `DATABASE_SETUP.md`
- **Python API:** See `PYTHON_API.md`
- **API Endpoints:** See `PYTHON_API.md` for full list

---

**Status:** ✅ Ready for Development  
**Last Updated:** February 11, 2026  
**Version:** 1.0.0
