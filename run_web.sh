#!/bin/bash

# Web Interface Quick Start Script
# This script makes it easy to start the web interface

echo "🌐 Shift Scheduler Web Interface"
echo "=================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Install from: https://www.python.org/downloads/"
    exit 1
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "❌ Flask not found. Installing dependencies..."
    echo ""
    pip install -r requirements.txt
    echo ""
fi

# Show instructions
echo "✅ Ready to start!"
echo ""
echo "📊 Starting web interface on http://localhost:5000"
echo "💡 Press Ctrl+C to stop"
echo ""
echo "Next steps:"
echo "  1. Your browser will open automatically"
echo "  2. Add workers (👥)"
echo "  3. Add shifts (📅)"
echo "  4. Generate schedule (🎯)"
echo ""

# Start the server
python3 web_interface.py
