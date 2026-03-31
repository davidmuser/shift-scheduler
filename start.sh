#!/bin/bash
# Quick Start Script for Shift Scheduler SaaS

set -e

echo "🚀 Shift Scheduler SaaS - Quick Start"
echo "===================================="
echo ""

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Update .env with your Neon PostgreSQL DATABASE_URL"
    echo "   Edit .env and set DATABASE_URL to your Neon connection string"
fi

# Initialize database
echo "🗄️  Initializing database..."
python -c "
from web_interface import Base, engine, SessionLocal
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    Base.metadata.create_all(bind=engine)
    logger.info('✓ Database tables created successfully')
except Exception as e:
    logger.warning(f'Database warning: {e}')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting web server..."
echo "   Open: http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

python web_interface.py
