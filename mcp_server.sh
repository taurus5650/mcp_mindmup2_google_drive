#!/bin/bash

# Change to the script directory
cd "$(dirname "$0")"

# Set environment variables
export PYTHONPATH="$(pwd)"
export ENV="development"

# Run the MCP server
exec "$(pwd)/.venv/bin/python" "$(pwd)/main.py"