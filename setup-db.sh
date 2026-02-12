#!/bin/bash

# HHS Patient Portal - Database Setup Script
# This script sets up the PostgreSQL database for the patient portal

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  HHS Patient Portal - Database Setup                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  Warning: .env file not found. Using default values."
    DB_NAME="hhs_patient_portal"
    DB_USER="postgres"
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install it first:"
    echo "   Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "   macOS: brew install postgresql"
    exit 1
fi

echo "✅ PostgreSQL found"
echo ""

# Check if PostgreSQL is running
if ! sudo systemctl is-active --quiet postgresql 2>/dev/null && ! pgrep -x postgres > /dev/null; then
    echo "🔄 Starting PostgreSQL..."
    sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null || true
    sleep 2
fi

echo "✅ PostgreSQL is running"
echo ""

# Create database
echo "🔄 Creating database: $DB_NAME"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
echo "✅ Database created/verified"
echo ""

# Run schema
echo "🔄 Creating database schema..."
sudo -u postgres psql -d $DB_NAME -f server/db/schema.sql
echo "✅ Schema created successfully"
echo ""

# Optional: Run seed data
if [ -f server/db/seed.sql ] && [ -s server/db/seed.sql ]; then
    read -p "Do you want to load seed data? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Loading seed data..."
        sudo -u postgres psql -d $DB_NAME -f server/db/seed.sql
        echo "✅ Seed data loaded"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ Database setup complete!                           ║"
echo "║                                                        ║"
echo "║  Database: $DB_NAME"
echo "║  User: $DB_USER"
echo "║                                                        ║"
echo "║  Next steps:                                           ║"
echo "║  1. Update .env with your database credentials         ║"
echo "║  2. Run: npm run server                                ║"
echo "╚════════════════════════════════════════════════════════╝"
