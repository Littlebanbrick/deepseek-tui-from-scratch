from openai import OpenAI
from rich.console import Console
from rich.text import Text

console = Console()

class ChatBot:
    def __init__(self, config):
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.show_thinking = config["show_thinking"]
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        
        # Save the latest thinking
        self.last_reasoning = ""
        
    def toggle_thinking(self):
        self.show_thinking = not self.show_thinking
        return "ON" if self.show_thinking else "OFF"

    def send_message(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        extra_body = {}
        if "deepseek-chat" in self.model or "deepseek-reasoner" in self.model:
            extra_body["thinking"] = {"type": "enabled"}

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            stream_options={"include_usage": True},
            extra_body=extra_body
        )

        reasoning_buffer = []
        content_buffer = []
        current_role = None

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            reasoning_text = getattr(delta, "reasoning_content", None) or ""
            if reasoning_text:
                if current_role != "thinking" and content_buffer:
                    console.print()
                self.last_reasoning += reasoning_text
                if self.show_thinking:
                    console.print(reasoning_text, end="", style="dim")
                reasoning_buffer.append(reasoning_text)
                current_role = "thinking"

            content_text = delta.content or ""
            if content_text:
                if current_role == "thinking":
                    console.print("\n[Assistant]: ", end="")
                elif current_role is None:
                    console.print("[Assistant]: ", end="")
                console.print(content_text, end="", style="bold")
                content_buffer.append(content_text)
                current_role = "content"

        console.print()

        full_response = "".join(content_buffer)
        self.messages.append({"role": "assistant", "content": full_response})
        return full_response