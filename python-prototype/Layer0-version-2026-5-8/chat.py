import os
import json
import uuid
import requests
import redis
from dotenv import load_dotenv

# ---------- Config ----------
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    exit("ERROR: DEEPSEEK_API_KEY not set in .env file")

REDIS_HOST = "localhost"
REDIS_PORT = 6379
SESSION_PREFIX = "session:"
EXPIRE_SECONDS = 1800       # 30 minutes, set to a large value for quasi-permanent
MAX_MESSAGES = 40           # how many recent messages to keep (user+assistant)

# ---------- Redis connection ----------
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ---------- Session management ----------
session_id = input("Session ID (leave blank to start new): ").strip()
if not session_id:
    session_id = str(uuid.uuid4())
    print(f"New session created: {session_id}")
else:
    print(f"Resuming session: {session_id}")

key = f"{SESSION_PREFIX}{session_id}"

# ---------- Load history from Redis ----------
messages = []
stored = r.get(key)
if stored:
    messages = json.loads(stored)
    print(f"Restored {len(messages)} messages from previous session.")

# ---------- Helper: truncate message list ----------
def truncate_messages(msgs, max_count=MAX_MESSAGES):
    """Keep system message (if present) and the most recent messages."""
    if not msgs:
        return msgs

    system_count = 1 if msgs[0]["role"] == "system" else 0
    if len(msgs) <= max_count:
        return msgs

    preserved = msgs[:system_count]
    recent = msgs[-(max_count - system_count):]
    return preserved + recent

# ---------- Chat loop ----------
print("Chat started. Type 'exit' to quit.")
while True:
    user_input = input(f"[{session_id[:8]}...] You: ")
    if user_input.lower() == "exit":
        print("Goodbye!")
        # Save final state before exit
        if messages:
            r.setex(key, EXPIRE_SECONDS, json.dumps(messages))
        break

    # Append user message
    messages.append({"role": "user", "content": user_input})

    # Call DeepSeek API
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "deepseek-chat", "messages": messages}
    )

    if resp.status_code == 200:
        reply = resp.json()["choices"][0]["message"]["content"]
        print(f"Assistant: {reply}")
        messages.append({"role": "assistant", "content": reply})

        # Truncate history to keep context manageable
        messages = truncate_messages(messages)

        # Persist to Redis and refresh TTL
        r.setex(key, EXPIRE_SECONDS, json.dumps(messages))
    else:
        print(f"API error: {resp.status_code} - {resp.text}")
        # Remove the just‑added user message to avoid polluting history
        messages.pop()
        
"""
若将 EXPIRE_SECONDS 设为非常大的值（如 60*60*24*365），再配合 Redis 的持久化（RDB/AOF），可接近无限期保存会话。
真正的生产级方案会在此基础上加入数据库（以上未实现，但代码结构容易扩展）。
"""