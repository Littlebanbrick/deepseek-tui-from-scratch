from prompt_toolkit.layout import Layout, HSplit, Window, Float, FloatContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import HTML, merge_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application
from prompt_toolkit.styles import Style
import asyncio


class MessageList:
    """Manages chat messages and an optional streaming message."""

    def __init__(self):
        self.messages = []
        self.streaming_message = None
        self._on_update = None

    def set_update_callback(self, callback):
        self._on_update = callback

    def add_message(self, msg_type, content):
        self.messages.append({"type": msg_type, "content": content})
        self._trigger_update()

    def start_streaming(self, msg_type):
        self.streaming_message = {"type": msg_type, "content": "", "buffer": []}
        self._trigger_update()

    def append_streaming(self, text):
        if self.streaming_message:
            self.streaming_message["buffer"].append(text)
            self.streaming_message["content"] = "".join(self.streaming_message["buffer"])
            self._trigger_update()

    def finish_streaming(self, final_content=None):
        if self.streaming_message:
            if final_content is not None:
                self.streaming_message["content"] = final_content
            self.messages.append(self.streaming_message)
            self.streaming_message = None
            self._trigger_update()

    def _trigger_update(self):
        if self._on_update:
            self._on_update()

    def render(self):
        """Return FormattedText for the entire message area."""
        lines = []
        for msg in self.messages:
            lines.extend(self._render_message(msg))
        if self.streaming_message:
            lines.extend(self._render_message(self.streaming_message, is_streaming=True))
        return merge_formatted_text(lines)

    def _render_message(self, msg, is_streaming=False):
        content = msg["content"]
        if msg["type"] == "user":
            prefix = HTML("<ansigreen><b>You:</b></ansigreen> ")
            return [prefix, ("user_message", "\n" + content)]
        elif msg["type"] == "thinking":
            prefix = HTML("<ansigray><b>Thinking:</b></ansigray> ")
            return [prefix, ("thinking", " " + content + "\n")]
        elif msg["type"] == "assistant":
            prefix = HTML("<ansiblue><b>Assistant:</b></ansiblue> ")
            return [prefix, ("assistant", " " + content + "\n\n")]
        elif msg["type"] == "error":
            return [("error", f"Error: {content}\n")]
        elif msg["type"] == "warning":
            return [("warning", f"Warning: {content}\n")]
        else:
            return [("", content + "\n")]


class ChatApplication:
    def __init__(self, config):
        self.config = config
        self.bot = None
        self.show_thinking = config["show_thinking"]
        self.message_list = MessageList()

        # Input field
        self.input_field = TextArea(
            height=3,
            prompt="> ",
            style="class:input_field",
            multiline=False,
            wrap_lines=True,
        )

        # Top status bar
        self.status_control = FormattedTextControl(HTML("<b>DeepSeek Chat</b>"))
        self.status_window = Window(content=self.status_control, height=1, style="class:status_bar")

        # Message area
        self.message_control = FormattedTextControl(
            text=self.message_list.render, focusable=False
        )
        self.message_window = Window(
            content=self.message_control, wrap_lines=True, always_hide_cursor=True
        )

        # Layout with a float for the thinking indicator
        self.root_container = FloatContainer(
            content=HSplit([
                self.status_window,
                Window(height=1, char="-", style="class:separator"),
                self.message_window,
                Window(height=1, char="-", style="class:separator"),
                self.input_field,
            ]),
            floats=[
                Float(
                    Window(
                        FormattedTextControl(self._get_thinking_status),
                        width=15,
                        height=1,
                        style="class:thinking_status",
                    ),
                    right=0,
                    top=0,
                )
            ],
        )

        # Key bindings
        self.kb = KeyBindings()

        @self.kb.add("c-t")
        def toggle_thinking(event):
            if self.bot:
                self.bot.toggle_thinking()
                self.show_thinking = self.bot.show_thinking
                self.message_list.finish_streaming()
                self.app.invalidate()

        @self.kb.add("c-c")
        def quit_app(event):
            event.app.exit()

        @self.kb.add("enter")
        def send_message(event):
            user_input = self.input_field.text.strip()
            if not user_input:
                return
            self.input_field.text = ""
            self.message_list.add_message("user", user_input)
            asyncio.ensure_future(self._handle_user_message(user_input))

        # Application
        self.app = Application(
            layout=Layout(self.root_container),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=False,
            style=self._get_style(),
        )

        self.current_task = None

    def _get_style(self):
        return Style([
            ("status_bar", "bg:#333333 fg:white"),
            ("separator", "fg:#444444"),
            ("input_field", "bg:#1e1e1e fg:white"),
            ("user_message", "fg:white"),
            ("assistant", "fg:white"),
            ("thinking", "fg:gray"),
            ("error", "fg:ansired"),
            ("warning", "fg:ansiyellow"),
            ("thinking_status", "bg:#333333 fg:white"),
        ])

    def _get_thinking_status(self):
        state = "ON" if self.show_thinking else "OFF"
        color = "green" if state == "ON" else "red"
        return HTML(f"Thinking: <{color}>{state}</{color}>")

    async def _handle_user_message(self, user_input):
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        try:
            current_mode = None
            async for event_type, text in self.bot.send_message(user_input):
                if event_type == "thinking":
                    if current_mode != "thinking":
                        self.message_list.start_streaming("thinking")
                        current_mode = "thinking"
                    self.message_list.append_streaming(text)
                elif event_type == "content":
                    if current_mode != "assistant":
                        self.message_list.finish_streaming()
                        self.message_list.start_streaming("assistant")
                        current_mode = "assistant"
                    self.message_list.append_streaming(text)
            self.message_list.finish_streaming()
        except Exception as e:
            self.message_list.add_message("error", str(e))
        finally:
            self.app.invalidate()

    async def run(self):
        from chat import ChatBot
        self.bot = ChatBot(self.config)
        await self.app.run_async()