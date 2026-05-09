# DeepSeek Chat - Configuration
# Modify values here; do NOT hardcode them in chat.py

import os
from dotenv import load_dotenv

load_dotenv()

# --- API ---
API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEFAULT_MODEL = "deepseek-v4-flash"

# --- Redis ---
REDIS_HOST = "localhost"
REDIS_PORT = 6379
SESSION_PREFIX = "session:"
EXPIRE_SECONDS = 1800           # 30 minutes

# --- Messages ---
MAX_MESSAGES = 40               # how many recent messages to keep
REASONING_EFFORT = "high"       # "high" or "max"