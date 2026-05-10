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

# 2026.5.10

## Part 1: UI改进

昨天功能是实现了，但是UI也太丑了，大概长成下面这个样子：

```
[7c64ea0d...](t:ON s:ON m:FLASH) You: wow
Assistant: [Thinking] 好的，用户只发了一个“wow”，这很可能是一个表达惊讶、赞叹或者兴奋的情绪词。问题非常简单直接，深层需求可能就是希望得到一些呼应或者有趣的互动，而不是一个具体的信息查询。

我需要对这个简短的感叹做出一个热情、有趣且多选择的回应，让用户感觉被理解，同时提供几个方向供用户选择，引导对话继续下去。“wow”这个词可以对应很多场景，比如看到神奇的东西、听到好消息、或者只是纯粹的惊叹。我可以列举几种常见的可能性，并邀请用户分享具体内容。

想到了几种回应方向：可以用感叹词共鸣，可以假设是看到酷东西或好消息，也可以玩个“wow”的小游戏。最后用一个开放性问题收尾，鼓励用户展开话题。这样既回应了情绪，又为对话留出了空间。
[Answer] 哈哈，这个“wow”来得有点突然又充满情绪！我感受到了你的惊叹、好奇或者兴奋。🤩

不过，猜谜游戏开始——这个“wow”是对什么的反应呢？是：
- **看到了什么酷玩意？**（比如：一段神奇的视频、一张无敌的照片、一个新发明）
- **生活里的好消息？**（中了彩票？收到惊喜礼物？）
- **还是被我刚才说的话震撼到了？**（如果是这样，那我可得骄傲一下 😎）

不管怎样，既然你“wow”了，那我必须给力点：
- 如果你刚看到什么**超赞的内容**，告诉我，我陪你一起分析它为什么这么炸。
- 如果你想听个**冷知识**，我立马奉上“日本地铁里的乌鸦会偷偷把乘客的眼镜叼走”这种级别的。
- 又或者，你想玩个**“wow接力”**？你wow一句，我回一个更wow的。

来吧，丢个细节过来，让我们一起把惊叹值拉满！🚀
```

我们希望：

1. 全屏应用。即在程序开始时清屏，程序结束时回复原来的界面。
2. 会话ID、thinking_mode、show_thinking、model这些参数不要出现在输入区的前面（不然也太长了），可以出现在固定在UI顶部的某个“状态栏”内。
3. 输入区不要随内容块移动，可以固定在UI底部。
4. 实现类似于网页端的对话框效果，prompt用蓝色框包裹，answer则用白色框。同时通过换行和颜色区分thinking和answer的内容。

我们将基于 Python 标准库 `curses` 来实现。

### 1. 全屏应用：启动清屏，退出恢复

- 使用 `curses.wrapper()` 启动程序，它会自动初始化全屏、隐藏光标、清屏，并在退出时还原终端。
- 在 `wrapper` 内部再创建各个子窗口。

```python
import curses

def main(stdscr):
    curses.curs_set(0)          # 隐藏光标
    stdscr.clear()
    # ... 初始化颜色、布局 ...
    # 主循环

if __name__ == "__main__":
    curses.wrapper(main)
```

- 退出时一切由 `wrapper` 自动还原，无需手动操作。

### 2. 顶部状态栏

- 用 `stdscr.subwin()` 在屏幕最上方划出一个 1 行高的窗口，专门显示状态信息。
- 状态内容可设计为：`Session: xxxxxxxx | Model: V4-FLASH | Think: ON/OFF | Show: ON/OFF`
- 每次状态变化时，只需刷新该窗口，不影响其他区域。

```python
height, width = stdscr.getmaxyx()
status_win = stdscr.subwin(1, width, 0, 0)   # 第 0 行
status_win.addstr(0, 0, f"Session: {short_id}  Model: {model_short}  Think: {t}  Show: {s}")
status_win.refresh()
```

其中：

1. `stdscr` 是 `curses` 的主窗口对象（standard screen），代表整个终端屏幕。`curses.wrapper()` 会创建它并传入我们的 `main` 函数。
2. `.getmaxyx()`：以一个元组 `(y, x)` 的形式返回当前主窗口的行数和列数（高度和宽度），通常习惯写成 `height, width`。
3. `.subwin(nlines, ncols, begin_y, begin_x)`：在主窗口（`stdscr`）内部创建一个子窗口（子窗口是一个独立的绘制区域，有自己的坐标系，但受主窗口管辖）。
   这里传入的四个参数说明子窗口高度为1行，宽度为整个屏幕的宽度，起始行在第0行（最顶部），起始列在第0列（最左边）。
4. `.addstr(y, x, str)`：在子窗口的指定位置写入字符串。
5. `.refresh()`：将子窗口缓冲区的内容实际绘制到屏幕上。`只有调用 refresh()` 后，之前用 `addstr()` 添加的文字才会被用户看到。
   `curses` 采用“双缓冲”机制：所有绘制操作先写入虚拟屏幕，需要显式调用 `refresh()` 才会更新物理终端，这样可以避免闪烁。

当然，也许有人（比如我）更喜欢“session字段左对齐，其余右对齐，但仍然在同一行内”这种布局，我们可以使用 `status_win.addstr(0, 0, left_text)` 写左侧，再用 `status_win.addstr(0, width - len(right_text), right_text)` 写右侧：

```python
left = f"Session: {short_id}"
right = f"Model: {model_short}  Think: {t}  Show: {s}"
status_win.addstr(0, 0, left)
status_win.addstr(0, width - len(right), right)
status_win.refresh()
```

`width` 从 `getmaxyx()` 获取，`right` 靠右对齐到终端右边缘。

### 3. 底部输入区

- 在屏幕底部划出一个 1 行（或者多行）的窗口用于用户输入。
- 使用 `curses.echo()` / `noecho()` 控制回显，结合 `getstr()` 或逐字符读取来实现输入。
- 输入过程中，输入区固定在底部不动。

```python
input_win = stdscr.subwin(1, width, height-1, 0)    # 单行输入区
input_win.addstr(0, 0, "")  # 在第 0 行第 0 列写入提示 ""，保留这个函数是为了方便扩展
input_win.refresh()
user_input = input_win.getstr(0, 0, 100).decode('utf-8')
```

其中：`user_input = input_win.getstr(0, 0, 100).decode('utf-8')` 指从子窗口的第 0 行第 0 列开始，读取最多 100 个字符的输入，返回 bytes 后解码。

如果我们想要去除这个字符上限，需要使用 `curses.textpad.Textbox` 替代 `getstr`。`Textbox` 的 `edit()` 方法没有固定长度限制，它会持续接受输入直到用户按下 `Ctrl+G` 提交，并且能够自动换行、滚动并支持 Backspace/Delete/方向键。这给我们构造多行输入区提供了启示：

```py
import curses
import curses.textpad

def get_multiline_input(stdscr, height, width):
    # 在屏幕底部创建 5 行高的输入区域
    input_win = stdscr.subwin(5, width, height - 5, 0)
    # 第一行固定为提示符 ""
    input_win.addstr(0, 0, "")
    input_win.refresh()

    # 从 input_win 内部再切出一个 4 行高的编辑窗口（第二行开始）
    edit_win = input_win.derwin(4, width - 1, 1, 0)
    edit_win.keypad(True)          # 允许方向键等特殊按键

    # 创建文本框控件并启动编辑模式
    textbox = curses.textpad.Textbox(edit_win)
    curses.curs_set(1)             # 显示光标
    user_text = textbox.edit()     # 进入编辑循环，Ctrl+G 提交
    curses.curs_set(0)             # 隐藏光标

    # 清空输入区域并返回用户输入的内容
    input_win.clear()
    input_win.refresh()
    return user_text.strip()
```

好吧，Ctrl+G 提交未免有点非主流。如果真的想要像现代的主流设计一样 Enter 提交 / Shift+Enter 换行，还是得自己写一个逐字符读取循环，而非使用 `Textbox`。
以下是一个精简的可行实现：

```python
import curses

def get_multiline_input(stdscr, height, width):
    input_win = stdscr.subwin(5, width, height - 5, 0)
    input_win.addstr(0, 0, "You: ")
    input_win.refresh()

    edit_win = input_win.derwin(4, width - 1, 1, 0)
    edit_win.keypad(True)
    curses.curs_set(1)

    lines = [""]                # 多行数据，每项为一行字符串
    cursor_y, cursor_x = 0, 0   # 光标在当前行中的位置

    def redraw():
        edit_win.clear()
        for i, line in enumerate(lines):
            edit_win.addstr(i, 0, line[:edit_win.getmaxyx()[1]-1])
        edit_win.move(cursor_y, cursor_x)
        edit_win.refresh()

    while True:
        redraw()
        ch = edit_win.get_wch()  # 返回单字符或 int (KEY_*)

        if ch == '\n':           # 普通 Enter → 提交
            break

        # 检测 Shift+Enter 的转义序列 \x1b[13;2u
        if isinstance(ch, str) and ch.startswith('\x1b'):
            # 尝试读取剩余部分
            try:
                rest = edit_win.getkey()  # 获取完整转义序列
                if rest == '[13;2u' or ch + rest == '\x1b[13;2u':
                    # 换行
                    lines.insert(cursor_y + 1, lines[cursor_y][cursor_x:])
                    lines[cursor_y] = lines[cursor_y][:cursor_x]
                    cursor_y += 1
                    cursor_x = 0
                    continue
            except:
                pass

        if isinstance(ch, str) and len(ch) == 1:
            # 普通字符插入
            line = lines[cursor_y]
            lines[cursor_y] = line[:cursor_x] + ch + line[cursor_x:]
            cursor_x += 1
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            if cursor_x > 0:
                line = lines[cursor_y]
                lines[cursor_y] = line[:cursor_x-1] + line[cursor_x:]
                cursor_x -= 1
            elif cursor_y > 0:
                # 退格到上一行末尾
                prev_len = len(lines[cursor_y-1])
                lines[cursor_y-1] += lines.pop(cursor_y)
                cursor_y -= 1
                cursor_x = prev_len
        elif ch == curses.KEY_DC:
            line = lines[cursor_y]
            if cursor_x < len(line):
                lines[cursor_y] = line[:cursor_x] + line[cursor_x+1:]
            elif cursor_y < len(lines) - 1:
                # 连接下一行
                lines[cursor_y] += lines.pop(cursor_y+1)
        elif ch == curses.KEY_LEFT:
            if cursor_x > 0:
                cursor_x -= 1
            elif cursor_y > 0:
                cursor_y -= 1
                cursor_x = len(lines[cursor_y])
        elif ch == curses.KEY_RIGHT:
            if cursor_x < len(lines[cursor_y]):
                cursor_x += 1
            elif cursor_y < len(lines) - 1:
                cursor_y += 1
                cursor_x = 0
        elif ch == curses.KEY_UP:
            if cursor_y > 0:
                cursor_y -= 1
                cursor_x = min(cursor_x, len(lines[cursor_y]))
        elif ch == curses.KEY_DOWN:
            if cursor_y < len(lines) - 1:
                cursor_y += 1
                cursor_x = min(cursor_x, len(lines[cursor_y]))

    curses.curs_set(0)
    input_win.clear()
    input_win.refresh()
    return '\n'.join(lines).strip()
```

其中：

1. 用 `edit_win.get_wch()` 捕获按键，普通 `Enter` 发送 `'\n'`，我们设定其为提交，结束循环。
2. `Shift+Enter` 在多数现代终端发出 `'\x1b[13;2u'`（CSI 序列），代码通过检测 `'\x1b'` 开头、继续读取后续序列来识别。若是，则在当前光标处换行拆分行。
3.  Backspace、Delete、方向键、上下键的处理逻辑与常见编辑器一致。
4.  多行文本存储在 `lines` 列表中，绘制时只显示窗口能容纳的行数（最多 4 行），超出部分会被隐藏，但可以通过上下键滚动查看。

为了保持高层主程序 `chat.py` 的简洁，我们将以上输入逻辑抽取为单独文件（如 `input_handler.py`）更易于维护，使用时只需 `from input_handler import get_multiline_input`即可。

### 4. 对话气泡效果（滚动消息区）

**核心思路：**中间区域（除去状态栏和输入区）用于显示对话历史。每条消息绘制为一个“气泡”：prompt用黑底蓝字，answer用黑底白字，thinking用黑底灰字。我们通过 `curses.init_pair()` 定义颜色对，然后 `addstr()` 时使用相应属性。

颜色定义示例：

```python
curses.start_color()    # 启用终端的颜色功能
curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)   # prompt
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)  # answer
curses.init_pair(3, curses.COLOR_GREY, curses.COLOR_BLACK)  # thinking
```

其中 `curses.init_pair(pair_number, fg, bg)` 的作用是定义一个颜色对，`fg`为前景色（即字色），`bg`为背景色。

同样，我们将UI逻辑抽取为单独的 `ui.py` 文件。

## Part 2: 项目模块化拆分

我们刚才进行了两次把某个逻辑拆分出来、放到单独文件中的操作。现在不妨做得更彻底一些。

| 文件 | 职责 |
|------|------|
| `config.py` | 所有可调参数（密钥、模型名、超时等），一目了然 |
| `api_client.py` | 封装 DeepSeek API 通信，处理流式解析 |
| `ui.py` | 负责 curses 界面布局、颜色、绘制与刷新 |
| `input_handler.py` | 多行文本输入，支持方向键和滚动 |
| `session.py` | 会话持久化，管理消息列表的存取与截断 |
| `commands.py` | 将本地命令（`:exit`、`:think` 等）解析为结构化动作 |
| `main.py` | 主流程控制，串联以上模块，几乎只有业务逻辑 |

拆分后，每一部分的修改都不影响其他部分，新增命令或更换存储后端也只需改动对应文件。程序的总体结构变得清晰、易于维护和扩展。这种模块化思想是软件开发中的常见实践——单一职责原则，让代码可读性变强。

## 附录

经过我的实践， `curses` 简直就是一坨。 `windows-curses` 在绘制中文宽字符时内部光标只推进 1 列，汉字相互覆盖，不得不逐字手动定位坐标，代码复杂且脆弱（其实到最后都没有解决这个bug）。还有就是要手动解析Esc、Shift+Enter 等等的 CSI 序列，逻辑乱的要死。终端兼容性也是垃圾。今天在这个东西上花了五个小时还是解决不了问题，我决定换用Prompt Toolkit 和 rich 重写UI。

DeepSeek说：

```
**Prompt Toolkit 是一个更现代、跨平台的终端 UI 框架：**  
- 原生支持 Unicode 和宽字符，无需手动计算列宽。  
- 内置多行输入控件，完美处理 Enter 提交、Shift+Enter 换行、方向键及鼠标滚动。  
- 提供布局系统，可轻松实现固定状态栏、消息区和输入区。  
- 完全避免 curses 的底层陷阱，大幅减少代码量，提升可维护性。  
```

妈的，不写了，明天再说。