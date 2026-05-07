from config import get_config
from chat import ChatBot

def main():
    print("DeepSeek llm.")
    print("Enter 'quit' to quit.")
    print("Enter '/thinking' to enable thinking display.")
    print("-" * 40)
    
    try:
        config = get_config()
        bot = ChatBot(config)
    except Exception as e:
        print(f"Startup error: {e}")
        return
    
    # The main loop
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit"]:
                print("Bye!")
                break
            if not user_input.strip():
                continue
            if user_input.lower() == "/thinking":
                state = bot.toggle_thinking()
                print(f"Thinking: {state}")
                continue
                
            bot.send_message(user_input)
            
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()