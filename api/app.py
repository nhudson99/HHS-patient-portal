"""
HHS Patient Portal - Flask API Server
HIPAA-compliant backend with secure authentication and audit logging
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from dotenv import load_dotenv
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database and utilities
from api.db.connection import init_db_pool, close_db_pool
from api.utils.session_manager import cleanup_expired_sessions
from api.utils.audit_log import cleanup_old_audit_logs
from api.routes.auth import auth_bp
from api.routes.events import events_bp
from api.routes.patients import patients_bp
from api.routes.patient_properties import patient_properties_bp
from api.routes.documents import documents_bp
from api.routes.appointments import appointments_bp

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SESSION_SECRET', 'dev-secret-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max upload size

# Security middleware - HIPAA compliance
if os.getenv('NODE_ENV') == 'production':
    # Force HTTPS in production
    Talisman(app, force_https=True, strict_transport_security_max_age=31536000)

# CORS configuration
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
CORS(app, 
     origins=allowed_origins,
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'])

# Rate limiting - prevent brute force attacks
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute", "1000 per hour"],
    storage_uri="memory://",
    default_limits_exempt_when=lambda: False
)

# Make limiter available for import in other modules
app.limiter = limiter

# Apply specific rate limiting to login
@app.before_request
def before_request():
    """Rate limiting is handled by decorator on specific routes"""
    pass

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': os.popen('date').read().strip()
    }), 200

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(events_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(patient_properties_bp)
app.register_blueprint(documents_bp)
app.register_blueprint(appointments_bp)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500 handler"""
    message = 'An error occurred' if os.getenv('NODE_ENV') == 'production' else str(error)
    return jsonify({'error': message}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Rate limit handler"""
    return jsonify({'error': 'Too many requests, please try again later'}), 429

# Background tasks for cleanup
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=cleanup_expired_sessions,
    trigger="interval",
    hours=1
)
scheduler.add_job(
    func=cleanup_old_audit_logs,
    trigger="interval",
    hours=1
)

def init_app():
    """Initialize application"""
    # Initialize database connection pool
    init_db_pool()
    
    # Start background scheduler
    scheduler.start()
    
    logger.info("""
╔════════════════════════════════════════════════════════╗
║                                                        ║
║   🏥 HHS Patient Portal API Server (Python/Flask)     ║
║                                                        ║
║   Status: Running                                      ║
║   Port: {port}                                           ║
║   Environment: {env}                              ║
║   HIPAA Compliance: ✅ Enabled                         ║
║                                                        ║
║   Features:                                            ║
║   • Secure authentication with bcrypt                  ║
║   • Session management with auto-timeout               ║
║   • Comprehensive audit logging                        ║
║   • Rate limiting & brute force protection             ║
║   • Account lockout mechanism                          ║
║   • Password strength enforcement                      ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
    """.format(
        port=os.getenv('PORT', 3000),
        env=os.getenv('NODE_ENV', 'development')
    ))

def shutdown():
    """Cleanup on shutdown"""
    try:
        scheduler.shutdown()
        close_db_pool()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == '__main__':
    try:
        init_app()
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 3000)),
            debug=os.getenv('NODE_ENV') != 'production'
        )
    except KeyboardInterrupt:
        shutdown()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        shutdown()
