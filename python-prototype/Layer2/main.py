import asyncio
from config import get_config
from ui import ChatApplication

async def main():
    try:
        config = get_config()
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    app = ChatApplication(config)
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())