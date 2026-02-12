# HHS Patient Portal - Database & API Setup Guide

## 🏥 Overview

The HHS Patient Portal now includes a **HIPAA-compliant** PostgreSQL database backend with secure authentication and comprehensive audit logging.

## 🔐 HIPAA Compliance Features

### Security Measures Implemented

✅ **Authentication & Access Control**
- Bcrypt password hashing with salt (12 rounds)
- Additional pepper salt stored separately in database
- Session-based authentication with automatic timeout (15 minutes default)
- Multi-factor password validation (length, complexity, special characters)
- Account lockout after failed login attempts (5 attempts, 30-minute lockout)

✅ **Audit Logging**
- All access to Protected Health Information (PHI) is logged
- Tracks: user ID, action, timestamp, IP address, user agent
- Minimum 7-year retention (configurable, HIPAA requires 6+ years)
- Cannot be disabled or tampered with

✅ **Session Management**
- Automatic session timeout after inactivity
- Secure session tokens (cryptographically random)
- Session tracking with IP and user agent validation
- Force logout from all devices on password change

✅ **Password Requirements**
- Minimum 8 characters
- Must contain: uppercase, lowercase, numbers, special characters
- Password expiration enforcement (90 days default)
- Prevents password reuse

✅ **Additional Security**
- Rate limiting on API endpoints
- CORS protection
- Helmet.js security headers
- SQL injection prevention
- XSS protection

## 📁 Database Schema

### Core Tables

#### `users`
- Stores authentication credentials
- Tracks login attempts and account status
- Password expiration tracking

#### `patients`
- Patient demographic information
- Linked to users table

#### `doctors`
- Doctor profiles and credentials
- License number tracking

#### `appointments`
- Patient-doctor appointments
- Status tracking (pending, confirmed, completed, cancelled)

#### `medical_documents`
- Medical records (lab results, prescriptions, imaging, etc.)
- File storage references

#### `audit_logs` (HIPAA Compliance)
- Complete audit trail of all system access
- Tracks who, what, when, where

#### `user_sessions` (HIPAA Compliance)
- Active session management
- Automatic expiration and cleanup

## 🚀 Setup Instructions

### Prerequisites

- Node.js v20+ (already installed)
- PostgreSQL 16 (installed via setup script)
- npm (already installed)

### 1. Database Setup

The database setup script handles everything automatically:

```bash
./setup-db.sh
```

This script will:
1. Check for PostgreSQL installation
2. Create the `hhs_patient_portal` database
3. Run the schema creation script
4. Optionally load seed data

### 2. Environment Configuration

A `.env` file has been created with default settings. Update these for production:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hhs_patient_portal
DB_USER=postgres
DB_PASSWORD=postgres  # ⚠️ CHANGE IN PRODUCTION

# Security Secrets (⚠️ MUST CHANGE IN PRODUCTION)
SESSION_SECRET=your_session_secret_here
JWT_SECRET=your_jwt_secret_here

# HIPAA Compliance Settings
SESSION_TIMEOUT_MINUTES=15
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=30
PASSWORD_EXPIRY_DAYS=90
```

**Generate secure secrets for production:**
```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

### 3. Running the Application

Start the backend API server:
```bash
npm run server
```

Start the frontend development server:
```bash
npm run dev
```

## 📡 API Endpoints

### Authentication

#### POST `/api/auth/register`
Register a new patient user.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "firstName": "John",
  "lastName": "Doe",
  "dateOfBirth": "1990-01-15",
  "phone": "555-0100"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "patient"
  }
}
```

#### POST `/api/auth/login`
Authenticate and create session.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "sessionToken": "abc123...",
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "patient"
  },
  "requirePasswordChange": false
}
```

#### POST `/api/auth/logout`
Invalidate current session.

**Headers:** `Authorization: Bearer <sessionToken>`

#### POST `/api/auth/change-password`
Change user password.

**Headers:** `Authorization: Bearer <sessionToken>`

**Request Body:**
```json
{
  "currentPassword": "OldPass123!",
  "newPassword": "NewSecurePass456!"
}
```

#### GET `/api/auth/me`
Get current user information.

**Headers:** `Authorization: Bearer <sessionToken>`

## 🗄️ Database Access

### Direct PostgreSQL Access

```bash
# Connect to database
sudo -u postgres psql -d hhs_patient_portal

# View tables
\dt

# Query users
SELECT id, username, email, role, created_at FROM users;

# View audit logs
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;
```

## 🔧 Development Scripts

```bash
# Frontend development
npm run dev              # Start Vite dev server (port 5173)
npm run build            # Build for production
npm run preview          # Preview production build

# Backend development
npm run server           # Start API server with hot reload (port 3000)
npm run server:build     # Compile TypeScript to JavaScript
npm run server:start     # Run compiled server

# Database
npm run setup:db         # Run database setup script
```

## 📊 Monitoring & Maintenance

### Automatic Cleanup Tasks

The server automatically performs these maintenance tasks every hour:

1. **Expired Sessions**: Removes inactive sessions older than the timeout period
2. **Old Audit Logs**: Archives logs older than retention period (default: 7 years)

### Manual Database Maintenance

```sql
-- View active sessions
SELECT user_id, ip_address, last_activity 
FROM user_sessions 
WHERE is_active = true;

-- Check failed login attempts
SELECT username, failed_login_attempts, last_failed_login
FROM users 
WHERE failed_login_attempts > 0;

-- View recent audit activity
SELECT u.username, al.action, al.timestamp, al.ip_address
FROM audit_logs al
JOIN users u ON al.user_id = u.id
ORDER BY al.timestamp DESC
LIMIT 20;
```

## 🛡️ Security Best Practices

### For Production Deployment

1. **Environment Variables**
   - Generate new SESSION_SECRET and JWT_SECRET
   - Use strong database password
   - Never commit .env to git

2. **Database Security**
   - Enable SSL connections (set `NODE_ENV=production`)
   - Use restricted database user (not postgres superuser)
   - Regular backups with encryption

3. **Network Security**
   - Use HTTPS only (configure reverse proxy)
   - Restrict CORS to known origins
   - Configure firewall rules

4. **Monitoring**
   - Set up alerts for failed login attempts
   - Monitor audit logs for suspicious activity
   - Track session patterns

5. **Data Protection**
   - Encrypt PHI at rest
   - Implement data backup strategy
   - Test disaster recovery procedures

## 📝 Password Requirements

Users must create passwords that meet these criteria:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*()_+-=[]{};':"\\|,.<>/?)

## 🔍 Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# View PostgreSQL logs
sudo journalctl -u postgresql
```

### Server Won't Start

```bash
# Check for port conflicts
lsof -i :3000

# View full error logs
npm run server 2>&1 | tee server.log
```

### Database Schema Issues

```bash
# Reset database (⚠️ DESTROYS ALL DATA)
sudo -u postgres psql -c "DROP DATABASE hhs_patient_portal;"
./setup-db.sh
```

## 📚 Additional Resources

- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Express Security Best Practices](https://expressjs.com/en/advanced/best-practice-security.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review audit logs for security events
3. Verify environment configuration
4. Contact system administrator

---

**Last Updated:** February 11, 2026
**Version:** 1.0.0
