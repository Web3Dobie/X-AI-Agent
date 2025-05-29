"""
Centralized configuration for file paths and directories.
Reads from environment variables with sensible defaults.
"""

import os

# Where to write generated chart PNGs (default D: to save C: space)
CHART_DIR = os.getenv("CHART_DIR", r"D:\charts")
# Where to save TA post markdown files
TA_POST_DIR = os.getenv("TA_POST_DIR", r"D:\TA_Posts")
# Where to keep weekly log backups
BACKUP_DIR = os.getenv("BACKUP_DIR", r"D:\X AI Agent\History")

# Data and log directories (relative to project by default)
DATA_DIR = os.getenv("DATA_DIR", "data")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# Ensure all directories exist
for directory in (CHART_DIR, TA_POST_DIR, BACKUP_DIR, DATA_DIR, LOG_DIR):
    os.makedirs(directory, exist_ok=True)
