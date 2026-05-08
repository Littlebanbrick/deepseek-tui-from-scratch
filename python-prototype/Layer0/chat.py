import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    exit("Please set DEEPSEEK_API_KEY in .env.")

prompt = input("Prompt: ")

resp = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
)

if resp.status_code == 200:
    print(resp.json()["choices"][0]["message"]["content"])
else:
    print(f"Error: {resp.status_code} {resp.text}")