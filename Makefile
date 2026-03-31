.PHONY: help run install clean test deps venv

# Default target
help:
	@echo "🚀 Shift Scheduler - Available Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  make run         - Start the Flask web server (http://localhost:5000)"
	@echo "  make install     - Install all dependencies in virtual environment"
	@echo "  make venv        - Create virtual environment (.venv)"
	@echo "  make deps        - Install dependencies from requirements.txt"
	@echo "  make clean       - Remove __pycache__ and .pyc files"
	@echo "  make test        - Run tests (if available)"
	@echo "  make help        - Show this help message"
	@echo ""

# Run the Flask application
run:
	@echo "🚀 Starting Shift Scheduler Web Interface..."
	@echo "📱 Open your browser to: http://localhost:5000"
	@echo "🛑 Press Ctrl+C to stop the server"
	@echo ""
	@if [ -d ".venv" ]; then \
		source .venv/bin/activate && python web_interface.py; \
	else \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi

# Install everything
install: venv deps
	@echo "✅ Installation complete!"
	@echo ""
	@echo "🚀 To start the server, run: make run"

# Create virtual environment
venv:
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
		echo "✅ Virtual environment created"; \
	else \
		echo "✅ Virtual environment already exists"; \
	fi

# Install dependencies
deps: venv
	@echo "📚 Installing dependencies..."
	@. .venv/bin/activate && pip install -q -r requirements.txt
	@echo "✅ Dependencies installed"

# Clean up Python cache files
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Run tests
test:
	@if [ -f "pytest.ini" ] || [ -d "tests" ]; then \
		. .venv/bin/activate && python -m pytest tests/ -v; \
	else \
		echo "⚠️  No tests found"; \
	fi

# Development server with auto-reload
dev: 
	@echo "🔄 Starting development server with auto-reload..."
	@echo "📱 Open your browser to: http://localhost:5000"
	@echo "🛑 Press Ctrl+C to stop"
	@echo ""
	@if [ -d ".venv" ]; then \
		source .venv/bin/activate && FLASK_ENV=development FLASK_DEBUG=1 python web_interface.py; \
	else \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
