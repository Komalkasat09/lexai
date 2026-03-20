#!/bin/bash

# Setup script for Contract Review Assistant Backend
# This script sets up the Python environment and installs dependencies

echo "=========================================="
echo "Contract Review Assistant - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PIP_CMD=pip3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
    PIP_CMD=pip
else
    echo "❌ Error: Python not found. Please install Python 3.9 or higher."
    exit 1
fi

echo "✓ Found Python: $PYTHON_CMD"
$PYTHON_CMD --version
echo ""

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    source venv/bin/activate
else
    source venv/Scripts/activate
fi
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
$PIP_CMD install --upgrade pip
echo ""

# Install dependencies
echo "Installing dependencies..."
$PIP_CMD install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
fi

# Run test
echo "=========================================="
echo "Running test pipeline..."
echo "=========================================="
echo ""
$PYTHON_CMD test_pipeline.py
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the API server:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the server: python main.py"
echo "  3. Visit http://localhost:8000/docs"
echo ""
