#!/bin/bash
echo "Setting up Python path..."
echo "PYTHONPATH before: $PYTHONPATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/../src:$PYTHONPATH"
echo "PYTHONPATH after: $PYTHONPATH"
echo "Don't forget to source the script: source scripts/setup_pythonpath.sh"
