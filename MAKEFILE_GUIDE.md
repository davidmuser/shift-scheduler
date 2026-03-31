# 🚀 Make Commands - Quick Start Guide

The project includes a `Makefile` for easy command execution. No need to remember complex commands!

## Quick Start

```bash
# Install everything and run
make install
make run
```

## Available Commands

### `make run` - Start the Application
```bash
make run
```
**What it does**:
- Starts the Flask web server
- Loads the virtual environment automatically
- Opens the app at http://localhost:5000
- Runs in foreground so you can see logs

**Output**:
```
🚀 Starting Shift Scheduler Web Interface...
📱 Open your browser to: http://localhost:5000
🛑 Press Ctrl+C to stop the server

* Running on http://127.0.0.1:5000
```

---

### `make install` - Complete Setup
```bash
make install
```
**What it does**:
1. Creates virtual environment (.venv) if it doesn't exist
2. Installs all dependencies from requirements.txt
3. Shows completion message

**Time**: ~30 seconds on first run

---

### `make venv` - Create Virtual Environment
```bash
make venv
```
**What it does**:
- Creates .venv directory with Python environment
- Safe to run multiple times (checks if exists)

---

### `make deps` - Install Dependencies
```bash
make deps
```
**What it does**:
- Installs all packages listed in requirements.txt
- Automatically activates venv
- Shows progress quietly

---

### `make clean` - Clean Up
```bash
make clean
```
**What it does**:
- Removes __pycache__ directories
- Removes .pyc compiled files
- Keeps code and virtual environment intact

---

### `make dev` - Development Mode
```bash
make dev
```
**What it does**:
- Starts Flask with auto-reload enabled
- Code changes trigger automatic restart
- Perfect for development

---

### `make test` - Run Tests
```bash
make test
```
**What it does**:
- Runs pytest tests if available
- Shows test results with verbose output

---

### `make help` - Show Help
```bash
make help
```
**What it does**:
- Displays all available commands
- Shows usage examples

---

## Common Workflows

### First Time Setup
```bash
make install
make run
```
Then open http://localhost:5000 in your browser.

### Daily Development
```bash
make run
```
Keep the terminal open while you work.

### Before Committing Code
```bash
make clean
make test
```

### Fresh Environment
```bash
rm -rf .venv
make install
make run
```

---

## How Make Works

Make looks for a file called `Makefile` in the current directory and executes the targets you specify.

**Basic syntax**:
```makefile
target_name:
    @command_to_run
```

The `@` symbol hides the command from output (cleaner display).

---

## Requirements

- **macOS/Linux**: Make is usually pre-installed
- **Windows**: Use WSL, Git Bash, or Windows Subsystem for Linux
- **Python**: 3.8+ required
- **Supported shells**: bash, zsh

---

## Troubleshooting

### Command not found: make
**Solution**: 
- macOS: Install Xcode Command Line Tools: `xcode-select --install`
- Linux: `sudo apt-get install build-essential`
- Windows: Use WSL or Git Bash

### Virtual environment not found when running `make run`
**Solution**: Run `make install` first

### Dependencies not installing
**Solution**: Check if requirements.txt exists: `ls requirements.txt`

### Port 5000 already in use
**Solution**: 
```bash
# Kill the process using port 5000
lsof -i :5000 | grep python | awk '{print $2}' | xargs kill -9

# Or change port in web_interface.py
```

---

## File Structure

```
shift-scheduler/
├── Makefile                 ← The command file
├── requirements.txt         ← Dependencies list
├── web_interface.py         ← Flask app
├── .venv/                   ← Virtual environment (created by make)
├── templates/               ← HTML templates
├── static/                  ← CSS, JS files
└── ...
```

---

## Next Steps

1. **First time users**: Run `make install && make run`
2. **Development**: Use `make dev` for auto-reload
3. **Cleanup**: Use `make clean` regularly
4. **Testing**: Use `make test` before commits

---

**Happy scheduling! 🎉**
