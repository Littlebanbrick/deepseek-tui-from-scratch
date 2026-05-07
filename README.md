# deepseek-tui-from-scratch

> A hands-on learning repository that reimplements the core of [DeepSeek-TUI](https://github.com/Hmbown/DeepSeek-TUI) — from a simple Python chat script to a Rust terminal agent — in order to deeply understand its architecture, design decisions, and engineering practices.

## Motivation

Instead of only reading source code, this project learns by **building the same feature set incrementally**, starting with a minimal “one‑day script” and progressively evolving it into a structured tool with TUI, tool use, session management and more. The goal is to match the internal architecture of DeepSeek-TUI, not just its behaviour.

## Roadmap

The process follows a **"functional accumulation layers"** approach:

- [x] **Layer 0** – Minimal chat loop with streaming ([`python-prototype`](python-prototype/))
- [ ] **Layer 1** – Streaming parser with reasoning / content separation
- [ ] **Layer 2** – Conversation persistence & multi‑turn memory
- [ ] **Layer 3** – Simple TUI interface (prompt_toolkit / ratatui)
- [ ] **Layer 4** – Tool system (file ops, shell commands)
- [ ] **Layer 5** – Agent modes, approval gates, session rollback
- [ ] **Layer 6** – Rust rewrite (the final TUI)

Each layer is built in the `python-prototype/` folder first, and later re‑implemented in Rust inside `rust-tui/`.

## Repository structure

```
deepseek-tui-from-scratch/
├── README.md
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── research/          # Source-code analysis notes
│   └── design/            # Design decisions & architecture drafts
│
├── python-prototype/      # Python stage — quick iteration
│   ├── main.py
│   ├── chat.py
│   ├── config.py
│   └── requirements.txt
│
├── rust-tui/              # Rust stage (created later)
│   └── ...
│
└── notes/
    └── learning-log.md    # Personal journal of discoveries & problems
    ```

## Getting started (Python prototype)

```bash
cd python-prototype
pip install -r requirements.txt
# Copy .env.example to .env and fill in your DeepSeek API key
python main.py
```

## Learning log

Check [`notes/learning-log.md`](notes/learning-log.md) for a chronicle of insights gained while tearing down the original repository, comparing codebases, and evolving the prototype.

## References

- Original project: [Hmbown/DeepSeek-TUI](https://github.com/Hmbown/DeepSeek-TUI)
- DeepSeek API docs: [api-docs.deepseek.com](https://api-docs.deepseek.com)
- Rust TUI library: [ratatui](https://ratatui.rs)