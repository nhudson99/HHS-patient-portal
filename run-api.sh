#!/bin/bash
# Run the HHS Patient Portal Python API Server

cd "$(dirname "$0")"
source venv/bin/activate
export PYTHONPATH=$(pwd)
python api/app.py
