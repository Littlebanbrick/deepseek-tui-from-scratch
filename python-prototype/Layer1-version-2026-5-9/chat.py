import sys
import json
import uuid
import requests
import redis
from config import (
    API_KEY, DEFAULT_MODEL,
    REDIS_HOST, REDIS_PORT, SESSION_PREFIX, EXPIRE_SECONDS,
    MAX_MESSAGES, REASONING_EFFORT
)

# ---------- Startup checks ----------
if not API_KEY:
    exit("ERROR: DEEPSEEK_API_KEY not set. Create a .env file or export the variable.")

# ---------- Redis connection ----------
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()
except redis.exceptions.RedisError as e:
    exit(f"ERROR: Cannot connect to Redis ({e})")

# ---------- Session ----------
session_id = input("Session ID (leave blank to start new): ").strip()
if not session_id:
    session_id = str(uuid.uuid4())
    print(f"New session created: {session_id}")
else:
    print(f"Resuming session: {session_id}")

key = f"{SESSION_PREFIX}{session_id}"

# ---------- Load history ----------
messages = []
try:
    stored = r.get(key)
    if stored:
        messages = json.loads(stored)
        print(f"Restored {len(messages)} messages from previous session.")
except (redis.exceptions.RedisError, json.JSONDecodeError) as e:
    print(f"Warning: Could not load history ({e}), starting fresh.")

# ---------- Helpers ----------
def truncate_messages(msgs, max_count=MAX_MESSAGES):
    if not msgs:
        return msgs
    system_count = 1 if msgs[0]["role"] == "system" else 0
    if len(msgs) <= max_count:
        return msgs
    preserved = msgs[:system_count]
    recent = msgs[-(max_count - system_count):]
    return preserved + recent

def save_to_redis():
    try:
        r.setex(key, EXPIRE_SECONDS, json.dumps(messages))
    except redis.exceptions.RedisError as e:
        print(f"\nWarning: Could not save session to Redis ({e})")

# ---------- Runtime toggles ----------
thinking_enabled = True
show_reasoning = True
current_model = DEFAULT_MODEL

# ---------- Chat loop ----------
print("Chat started. Use :exit to quit, :think :show :model to toggle.")
try:
    while True:
        # Status string
        model_short = current_model.split("-")[-1].upper()
        t_status = "ON" if thinking_enabled else "OFF"
        s_status = "ON" if show_reasoning else "OFF"
        status = f"t:{t_status} s:{s_status} m:{model_short}"

        try:
            user_input = input(f"[{session_id[:8]}...]({status}) You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            save_to_redis()
            break

        # --- Local commands ---
        if user_input.startswith(":"):
            cmd = user_input[1:].strip().lower()
            if cmd == "exit":
                save_to_redis()
                print("Goodbye!")
                break
            elif cmd == "think":
                thinking_enabled = not thinking_enabled
                if not thinking_enabled:
                    show_reasoning = False  # Close show_reasoning automatically
                    
                print(f"Deep thinking {'enabled' if thinking_enabled else 'disabled'}.")
            elif cmd == "show":
                show_reasoning = not show_reasoning
                print(f"Reasoning display {'ON' if show_reasoning else 'OFF'}.")
            elif cmd == "model":
                current_model = "deepseek-v4-pro" if current_model == "deepseek-v4-flash" else "deepseek-v4-flash"
                print(f"Model switched to {current_model}.")
            else:
                print("Available commands: :exit, :think, :show, :model")
            continue

        # --- Normal turn ---
        messages.append({"role": "user", "content": user_input})

        # Build request
        json_data = {
            "model": current_model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": False}
        }
        if thinking_enabled:
            json_data["thinking"] = {"type": "enabled"}
            json_data["reasoning_effort"] = REASONING_EFFORT

        # API call
        try:
            resp = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json=json_data,
                stream=True,
                timeout=60
            )
            if resp.status_code != 200:
                print(f"\nAPI error: {resp.status_code} - {resp.text}")
                messages.pop()
                continue
        except requests.exceptions.RequestException as e:
            print(f"\nNetwork error: {e}")
            messages.pop()
            continue

        # Stream processing
        partial_reasoning = ""
        partial_content = ""
        print("Assistant: ", end="", flush=True)

        if thinking_enabled and show_reasoning:
            print("[Thinking]", end=" ", flush=True)

        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})

                        reasoning = delta.get("reasoning_content", "")
                        if reasoning:
                            partial_reasoning += reasoning
                            if show_reasoning:
                                print(reasoning, end="", flush=True)

                        content = delta.get("content", "")
                        if content:
                            # Transition marker
                            if partial_reasoning and not partial_content and show_reasoning:
                                print("\n[Answer]", end=" ", flush=True)
                            print(content, end="", flush=True)
                            partial_content += content

                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
            print()

        except requests.exceptions.RequestException as e:
            print(f"\nStream interrupted: {e}")
        except KeyboardInterrupt:
            print("\nUser interrupted stream.")
        finally:
            # Save what we got
            if partial_content:
                messages.append({"role": "assistant", "content": partial_content})
                messages = truncate_messages(messages)
            else:
                # No answer, roll back user message
                messages.pop()
            save_to_redis()

except KeyboardInterrupt:
    print("\nChat interrupted. Saving session...")
    save_to_redis()
    print("Goodbye!")

except Exception as e:
    print(f"\nUnexpected error: {e}")
    save_to_redis()
    print("Session saved. Exiting.")