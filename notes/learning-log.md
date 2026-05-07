# 2026.5.7

学期内先做python部分，计划暑假学完Rust基础然后进行拆解。

Layer 0 — 最小可用的流式聊天循环

Python基础原型：一个能记住多轮对话、实时流式输出、通过 `.env` 安全加载密钥的 Python 聊天助手。

*   **配置分离**：`config.py` 从环境变量读取，避免密钥硬编码（对应DS-TUI的 `config.toml` 体系）
*   **状态管理**：`chat.py` 中的 `self.messages` 列表是多轮对话的“上下文窗口”雏形
*   **流式交互**：逐 chunk 打印的体验，对应 DS-TUI 中的实时渲染思考块
*   **错误隔离**：`main.py` 中的 try/except