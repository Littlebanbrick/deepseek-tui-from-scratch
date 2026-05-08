from openai import AsyncOpenAI

class ChatBot:
    def __init__(self, config):
        self.client = AsyncOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.show_thinking = config["show_thinking"]
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

    def toggle_thinking(self):
        self.show_thinking = not self.show_thinking
        return "ON" if self.show_thinking else "OFF"

    async def send_message(self, user_input: str):
        """Async generator yielding (type, text) chunks."""
        self.messages.append({"role": "user", "content": user_input})

        extra_body = {}
        if self.show_thinking:
            extra_body["thinking"] = {"type": "enabled"}

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            stream_options={"include_usage": True},
            extra_body=extra_body
        )

        full_content = ""

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            reasoning_text = getattr(delta, "reasoning_content", None) or ""
            if reasoning_text and self.show_thinking:
                yield ("thinking", reasoning_text)

            content_text = delta.content or ""
            if content_text:
                full_content += content_text
                yield ("content", content_text)

        self.messages.append({"role": "assistant", "content": full_content})