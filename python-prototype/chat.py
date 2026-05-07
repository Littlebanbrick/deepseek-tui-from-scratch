from openai import OpenAI

class ChatBot:
    def __init__(self, config):
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        # The system prompt is a great place to practice prompt engineering later.
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

    def send_message(self, user_input: str) -> str:
        """Send the user's message, get the reply in streaming mode,
        print it in real time, and return the full content."""
        # Add the user's message to the conversation history
        self.messages.append({"role": "user", "content": user_input})

        # Call the API with streaming enabled
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
        )

        print("Assistant: ", end="", flush=True)
        collected_content = []

        # Receive chunks one by one and print them in real time
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                collected_content.append(delta.content)

        print()  # newline
        full_response = "".join(collected_content)

        # Add the assistant's reply to the history for multi‑turn conversation memory
        self.messages.append({"role": "assistant", "content": full_response})
        return full_response