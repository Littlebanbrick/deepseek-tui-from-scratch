学期内先做python部分，计划暑假学完Rust基础然后进行拆解。

# 2026.5.7

Layer 0 — 最小可用的流式聊天循环

Python基础原型：一个能记住多轮对话、实时流式输出、通过 `.env` 安全加载密钥的 Python 聊天助手。

# 2026.5.8

## Part 1: 基本实现

Layer 0 基本实现：

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    exit("Please set DEEPSEEK_API_KEY in .env.")

while True:
    prompt = input("Prompt: ")

    if prompt.lower() == 'exit':
      break

    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    )

    if resp.status_code == 200:
        print(resp.json()["choices"][0]["message"]["content"])
    else:
        print(f"Error: {resp.status_code} {resp.text}")
```

其中：

1. `request.post(...)`会向目标服务器发起一个 POST 请求
2. `headers={...}` (请求头)：`Authorization` 字段携带 API 密钥 (以标准 `Bearer Token` 方式传递)
3. `json={...}` (请求体)：使用 `json=` 参数时，`requests` 会自动将 Python 字典转换为 JSON 格式，并设置好相应的 `Content-Type` 请求头

4. 响应体（body）原本是一串 JSON 格式的字符串，`.json()` 方法会把它解析成字典（dict）或列表（list），方便用键值对的方式访问数据。
5. 解析之后得到的格式大致如下（所以使用`["choices"][0]["message"]["content"]`这种看上去像是多维数组的结构访问模型的回复）：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "这里是模型的回复。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": { ... }
}
```

当然，这样的一个程序尽管能实现对话循环，却因为没有储存对话历史而无法连续对话。我们定义一个`messages`列表储存对话历史：

```python
messages = []

# 在对话循环中
    messages.append({"role": "user", "content": user_input})
    messages.append({"role": "assistant", "content": reply})
```

## Part 2: 会话持久化

现在又有新的问题：如果这样实现上下文，程序结束之后上下文就丢失了。要想维护多次启动间的上下文，生产环境中常采用数据库或专门的缓存系统。

这里以Redis为例展示如何轻量实现会话持久化。

>### 什么是Redis？
>
>Redis（Remote Dictionary Server）是一个开源的、基于内存的**键值**存储系统，常被用作数据库、缓存和消息代理。它的核心特点包括：
>
>- **极快的读写速度**：数据存储在内存中。
>- **丰富的数据结构**：不仅支持字符串（String），还支持哈希（Hash）、列表（List）、集合（Set）、有序集合（Sorted Set）等，方便用原生命令直接操作消息列表。
>- **持久化选项**：支持 RDB 快照和 AOF 日志，可在内存数据与磁盘间平衡。
>- **内置过期机制**：可为每个 key 设置 TTL（生存时间），到期自动删除，适合管理会话生命周期。
>- **发布/订阅与集群**：支持简单的消息队列模式，可方便地扩展为分布式集群。
>
>在会话持久化场景中，Redis 通常用于存储每个会话的完整消息历史（JSON 字符串或列表），并通过设置过期时间自动清理无用数据。

具体实现（在原有代码基础上补充）：

```python
import uuid
import redis
import json

# --- 连接 Redis ---
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# --- 获取或创建 session_id ---
session_id = input("输入会话 ID（留空则新建）: ").strip()
if not session_id:
    session_id = str(uuid.uuid4())
    print(f"新建会话 ID: {session_id}")
else:
    print(f"继续会话: {session_id}")

key = f"session:{session_id}"

# --- 从 Redis 加载历史消息 ---
messages = []
stored = r.get(key)
if stored:
    messages = json.loads(stored)

  # 在对话循环中，如果成功，将更新后的历史存回 Redis，设置过期时间
  r.setex(key, 1800, json.dumps(messages))
```

其中：

1. `uuid`：用于生成全局唯一的会话标识符，避免不同会话的 ID 冲突。
2. `r = redis.Redis(host='localhost', port=6379, decode_responses=True)`创建了 Redis 连接对象，连接到本地 Redis 服务（默认端口 6379）。`decode_responses=True` 让取出的数据自动解码为 Python 字符串，否则需要手动解码。
3. `session_id = input("输入会话 ID（留空则新建）: ").strip()`允许用户输入已有的会话 ID 来恢复历史。如果留空直接回车，则创建一个新会话。
4. `uuid4()` 生成随机 UUID，例如 `6f8c2a7e-...`，并转为字符串。该 ID 唯一，用于标识这次对话。如果输入了已有 ID，就复用该 ID 以加载对应的历史消息。
  
```python
if not session_id:
    session_id = str(uuid.uuid4())
    print(f"新建会话 ID: {session_id}")
else:
    print(f"继续会话: {session_id}")
```

5. 在 Redis 中使用的键名通过前缀 `session:` 与 ID 拼接，方便分类管理（例如`session:6f8c2a7e...`）。需要这个key是因为 Redis 是一个**键值对数据库**，所有数据在存取时都必须通过一个唯一的key来标识。

```python
key = f"session:{session_id}"
```

6. 先初始化空的 `messages` 列表。尝试从 Redis 获取该 key 对应的值。如果存在，说明这是旧会话，`json.loads` 将 JSON 字符串还原为 Python 列表，覆盖 `messages`，这样就能带着之前的上下文继续对话。

```python
messages = []
stored = r.get(key)
if stored:
    messages = json.loads(stored)
```

7. 在每轮成功获取助手回复后，将更新后的完整 `messages` 列表序列化为 JSON，重新写入 Redis。`setex` 设置字符串值的同时指定过期时间（秒），这里设为 1800 秒（30 分钟）。每次写入都会刷新过期计时器，保证只要会话活跃就不会被删除；若 30 分钟无操作，会话自动清除，避免无限堆积。

```python
r.setex(key, 1800, json.dumps(messages))
```

这样，即使程序退出后再启动，只要输入相同的会话 ID，就能从 Redis 中恢复完整的对话历史，实现跨启动的上下文持久化。

另外，比较合理的的用户友好设计是：将当前会话 ID 显示在提示符中，例如 `[session: abc123] Prompt:`，让用户随时可见以供记录。

```python
# 改为：
user_input = input(f"[{session_id[:8]}...] Prompt: ")
```

## Part 3: 无限期会话

不难看出，上述实现的会话“持久化”限定在30min（1800s）内。如果想要长期甚至无限期存储会话历史（就像DeepSeek网页端所做的那样），又该怎么做？

核心思路：Redis占用内存，不适合生产环境的长期存储。仅缓存最近活跃的会话，加速读写，设置 TTL（如30min，冷会话自动过期）。而永久存储所有消息的真实数据源可以采用数据库（如 PostgreSQL）。
>访问流程：  
>**请求 → 查 Redis → 未命中则查数据库 → 写入 Redis 缓存 → 更新并回写数据库和 Redis。**

关键实现步骤（伪代码，展示核心逻辑）:

```python
# 1. 从缓存或数据库加载历史
messages = r.get(session_key)
if not messages:
    messages = db.fetch(session_id)  # 从数据库查
    if messages:
        r.setex(session_key, 1800, json.dumps(messages))  # 回填缓存

# 2. 新消息追加到数据库（可异步）
db.append(session_id, user_msg, assistant_msg)

# 3. 更新 Redis 缓存并刷新过期时间
r.setex(session_key, 1800, json.dumps(messages))
```

## Part 4: 消息截断

推荐方式：保留最近 N 条消息，同时保护系统提示，以节省token。

核心思路：设定最大消息条数，例如 20 轮对话 = 40 条消息（user + assistant）。如果消息列表超过限制，保留系统消息（如有），然后截取末尾的 `MAX_MESSAGES - 系统消息条数` 条。

关键代码片段：

```python
MAX_MESSAGES = 40          # 最大消息条数
SYSTEM_COUNT = 1           # 系统提示数量（如果有）

if len(messages) > MAX_MESSAGES:
    # 保留开头系统消息，切除超出部分的旧消息
    preserved = messages[:SYSTEM_COUNT]
    recent = messages[-(MAX_MESSAGES - SYSTEM_COUNT):]
    messages = preserved + recent
```

# 2026.5.9

## Part 1: 流式输出

**原理：**

普通非流式请求：客户端发送整个请求 → 服务器生成完整回复 → 一次返回全部 JSON。用户必须等模型生成完所有文字才能看到响应。

而流式请求：
- 客户端在请求中加入 `"stream": true`。
- 服务器不会一次性返回完整结果，而是持续推送多个 HTTP 响应块（chunk）。
- 每个 chunk 是标准 **SSE（Server-Sent Events）** 格式，通常长这样：
  
  ```
  data: {"choices":[{"delta":{"content":"你"}}]}

  data: {"choices":[{"delta":{"content":"好"}}]}

  data: {"choices":[{"delta":{"content":"！"}}]}

  data: [DONE]
  ```

- 客户端一边收chunk一边打印，就能实现逐字输出。

DeepSeek API 完全兼容这种流式协议。

**实现方法：**

只需修改两处：
1. 请求体中加 `"stream": True`。类似这样：
   
   ```python
       resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "stream": True                # 开启流式
        },
        stream=True                       # 让 requests 不立即下载全部 body
    )
    ```

2. 将 `resp.json()` 改为遍历 `resp.iter_lines()` 解析 SSE 消息。
   ```python
    # 处理 SSE 流
    partial_content = ""
    print("Assistant: ", end="", flush=True)
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):   # SSE 协议中每个事件通常以 data: 开头
            data_str = line[6:]           # 去掉 "data: " 前缀
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    print(content, end="", flush=True)  # 逐字打印，不换行，立即输出
                    partial_content += content
            except json.JSONDecodeError:
                pass

    print()   # 换行

    # 最后，将完整回复追加到历史
    messages.append({"role": "assistant", "content": partial_content})
    ```

同时为了让 token 输出更平滑，可以在请求体的 JSON 字典中设置 `stream_options={"include_usage": False}`，以避免 DeepSeek 在流式响应的最后单独返回一个包含 token 用量但是 `delta` 为空的数据块，这样你的流式解析代码就只用处理 `delta.content`，不会被最后的空块干扰。

## Part 2: TRY & EXCEPT

在实际运行中，网络波动、服务端异常、用户中断等都会导致程序崩溃。添加 `try-except` 可以让程序更健壮，提供友好的错误提示，并在退出前安全保存会话。

**需要捕获的主要异常：**

| 异常类型 | 场景 | 处理方式 |
|---------|------|----------|
| `KeyboardInterrupt` | 用户按 `Ctrl+C` 中断 | 保存会话后优雅退出 |
| `requests.exceptions.RequestException` | 网络超时、DNS 失败、连接重置等 | 提示用户，跳过本轮，不丢失历史 |
| `json.JSONDecodeError` | 服务端返回非 JSON（比如网关错误） | 提示服务异常，保留用户输入 |
| `redis.exceptions.RedisError` | Redis 连接断开或写入失败 | 提示但继续对话，下次可能丢失持久化 |
| 其他通用 `Exception` | 未知错误 | 防止整个程序崩溃，保存退出 |

## Part 3: 深度思考

不难看出，目前的`chat.py`中还不支持深度思考模式。我们现在希望程序不仅可以开启深度思考，也可以让用户选择是否显示思考内容。以下以`deepseek-v4`为例说明如何做到这一点。

**实现方式：**
- 维护两个布尔变量：`thinking_enabled`（是否请求深度思考）、`show_reasoning`（是否将思考过程打印出来）。
- 在对话循环的 `input` 中，若用户输入的是本地命令（以 `:` 开头），则切换对应开关并打印状态，然后 `continue` 重新等待输入。
- 命令设计：
  - `:think` → 切换深度思考模式
  - `:show` → 切换是否显示思考内容
  - `:exit` 依旧退出
- 提示符中显示当前模式，如 `[t:ON s:ON] You: `。

**代码整合（在流式请求部分）**：

```python
# ---------- 新增：思考模式开关 ----------
thinking_enabled = True   # 默认开启深度思考
show_reasoning = True     # 默认显示思考内容

while True:
    # 生成带状态提示符
    status = f"t:{'ON' if thinking_enabled else 'OFF'} s:{'ON' if show_reasoning else 'OFF'}"
    try:
        user_input = input(f"[{session_id[:8]}...]({status}) You: ")
    except (EOFError, KeyboardInterrupt):
        ...

    # 处理本地命令
    if user_input.startswith(":"):
        cmd = user_input[1:].strip().lower()
        if cmd == "think":
            thinking_enabled = not thinking_enabled
            print(f"Deep thinking {'enabled' if thinking_enabled else 'disabled'}.")
        elif cmd == "show":
            show_reasoning = not show_reasoning
            print(f"Reasoning display {'ON' if show_reasoning else 'OFF'}.")
        elif cmd == "exit":
            break
        else:
            print("Unknown command. Available: :think, :show, :exit")
        continue

    # 正常对话框 ...
```

在构造 API 请求时，根据 `thinking_enabled` 动态组装参数：

```python
json_data = {
    "model": "deepseek-v4-flash",
    "messages": messages,
    "stream": True,
    "stream_options": {"include_usage": False}
}
if thinking_enabled:
    json_data["thinking"] = {"type": "enabled"}
    # 还可固定 reasoning_effort 为 "high" 或让用户通过命令调整
```

在流式解析中，根据 `show_reasoning` 决定是否打印思考内容：

```python
# 处理思考内容
reasoning_chunk = delta.get("reasoning_content", "")
if reasoning_chunk and show_reasoning:
    print(reasoning_chunk, end="", flush=True)
partial_reasoning += reasoning_chunk

# 处理回答内容（必须打印）
content_chunk = delta.get("content", "")
if content_chunk:
    if partial_reasoning and not partial_content and show_reasoning:
        print("\n--- Answer ---", flush=True)
    print(content_chunk, end="", flush=True)
    partial_content += content_chunk
```

**关于为什么不使用快捷键 Ctrl+T 进行模式切换：**

在标准终端中，`Ctrl+T` 通常被保留（如 Unix 信号的 `SIGINFO`），程序级的 `input()` 无法可靠捕获。使用 `pynput` 等库会引入重依赖。另外，在纯命令行 `input()` 中捕获全局组合键本身很复杂（需要监听线程或平台特定库）。上述命令方式能达到相同目的，且跨平台、无额外依赖。

## Part 4: 单独的配置加载文件

在项目的演化中，我们将所有可调整的配置（API 密钥、模型名称、Redis 连接信息、消息条数限制、过期时间等）从 `chat.py` 中抽离到单独的 `config.py` 文件中。打开 `config.py` 即可看到当前使用的模型、超时时间等所有关键参数，无需在主逻辑代码中翻找。当需要临时切换模型或修改缓存过期时间时，直接更改一两个变量即可，不易出错。

**代码示例：**

```python
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
```

同时，在`chat.py`中作相应修改即可。