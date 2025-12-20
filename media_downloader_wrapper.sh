#!/bin/bash

# Activate the virtual environment
source "/Users/jadennation/DEV/bin/.venv/bin/activate"

# Execute the media_downloader.py script
python "/Users/jadennation/DEV/bin/media_downloader.py" "$@"

# Deactivate the virtual environment (optional, but good practice if not needed afterwards)
# deactivate
