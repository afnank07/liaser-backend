import asyncio
import sys
import argparse
import logging
import requests
from typing import List, Optional
from telethon import TelegramClient, errors, events
from telethon.tl.types import User
from config import TelegramConfig
from dotenv import load_dotenv
import os 
import google.generativeai as genai

# --- Setup API keys ---
load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_sender.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramSender:
    """Main class for sending Telegram messages using the Client API."""
    
    def __init__(self):
        """Initialize the Telegram sender with configuration."""
        try:
            self.config = TelegramConfig()
            self.client = TelegramClient(
                self.config.get_session_name(),
                self.config.get_api_id(),
                self.config.get_api_hash()
            )
            self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=self.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize TelegramSender: {e}")
            raise
    
    async def connect(self):
        """Connect to Telegram and authenticate if necessary."""
        try:
            await self.client.start(phone=self.config.get_phone_number())
            logger.info("Successfully connected to Telegram")
            
            # Get information about the authenticated user
            me = await self.client.get_me()
            logger.info(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
            
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Telegram."""
        await self.client.disconnect()
        logger.info("Disconnected from Telegram")
    
    async def resolve_username(self, username: str) -> Optional[User]:
        """
        Resolve a username to a Telegram user.
        
        Args:
            username: The username to resolve (with or without @)
        
        Returns:
            User object if found, None otherwise
        """
        # Remove @ if present
        clean_username = username.lstrip('@')
        
        try:
            entity = await self.client.get_entity(clean_username)
            if isinstance(entity, User):
                return entity
            else:
                logger.warning(f"@{clean_username} is not a user (might be a channel or group)")
                return None
        except errors.UsernameNotOccupiedError:
            logger.error(f"Username @{clean_username} not found")
            return None
        except errors.UsernameInvalidError:
            logger.error(f"Username @{clean_username} is invalid")
            return None
        except Exception as e:
            logger.error(f"Error resolving username @{clean_username}: {e}")
            return None
    
    async def send_message(self, username: str, message: str) -> bool:
        """
        Send a message to a specific username.
        
        Args:
            username: The username to send to (with or without @)
            message: The message to send
        
        Returns:
            True if successful, False otherwise
        """
        user = await self.resolve_username(username)
        if not user:
            return False
        
        try:
            await self.client.send_message(user, message)
            logger.info(f"Message sent successfully to @{username}")
            return True
        except errors.FloodWaitError as e:
            logger.error(f"Rate limited. Need to wait {e.seconds} seconds")
            return False
        except errors.PeerFloodError:
            logger.error("Too many requests. Please try again later")
            return False
        except Exception as e:
            logger.error(f"Failed to send message to @{username}: {e}")
            return False

    # Placeholder for OpenAI support
    def generate_intro_openai(self, product_summary, target_description):
        # Implement OpenAI API call here in future
        return "Hi! I'd love to introduce you to a new product."
        
    # Generate initial message using Gemini
    def generate_intro_gemini(self, product_summary, target_description):
        # Replace with your Gemini API key
        
        # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        prompt = f"You are an outreach agent. Write a friendly, concise intro message to a Telegram user describing the following product: {product_summary}. The target person is: {target_description}. Your goal is to get them interested in chatting with the founder about using the product."
        
        # payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            final_context = response.text.strip()
            return final_context
        except Exception as e:
            print(f"Gemini API error: {e}")
            return "Hi! I'd love to introduce you to a new product."

    # Use Gemini to generate a response to the user's reply
    # def generate_reply_gemini(self, product_summary, target_description, user_reply):
    #     prompt = f"You are an outreach agent. You introduced the product: {product_summary} to a person described as: {target_description}. They replied: '{user_reply}'. Write a friendly, concise follow-up message to keep the conversation going and check if they are open to chatting with the founder about using the product."
    #     try:
    #         model = genai.GenerativeModel('gemini-1.5-flash')
    #         response = model.generate_content(prompt)
    #         return response.text.strip()
    #     except Exception as e:
    #         print(f"Gemini API error: {e}")
    #         return "Thanks for your reply! Would you be open to a quick chat with the founder?"

    # # Use Gemini to generate next reply, with chat history
    def generate_reply_gemini(self, product_summary, target_description, user_reply, history=None):
        history_str = "\n".join([f"{msg['role']}: {msg['text']}" for msg in history]) if history else ""
        prompt = f"You are an outreach agent. You introduced the product: {product_summary} to a person described as: {target_description}.\nConversation history:\n{history_str}\nThey replied: '{user_reply}'. Your goal is to keep the conversation going and close it if the person agrees or disagrees to meet the founder for a quick chat about the product. If they agree, thank them and end the conversation. If they disagree, politely thank them and end the conversation."
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API error: {e}")
            return "Thanks for your reply! Would you be open to a quick chat with the founder?"

    # Let Gemini decide if the conversation should close
    def check_conversation_status_gemini(self, product_summary, target_description, history):
        history_str = "\n".join([f"{msg['role']}: {msg['text']}" for msg in history]) if history else ""
        prompt = f"You are an outreach agent. Here is the conversation history with a Telegram user about the product: {product_summary}. The target person is: {target_description}.\nConversation history:\n{history_str}\nHas the user agreed to meet the founder for a quick chat about the product? Reply with 'AGREED', 'DISAGREED', or 'CONTINUE'."
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            status = response.text.strip().upper()
            return status
        except Exception as e:
            print(f"Gemini API error (status check): {e}")
            return "CONTINUE"
                     
    async def interactive_mode(self, product_summary, target_description, username):
        """Interactive mode for sending messages."""
        print("\n=== Telegram Message Sender - Interactive Mode ===")
        print("Type 'quit' or 'exit' to stop")

        try:
            # Collect product and target info
            # product_summary = input("Enter a summary of your product: ").strip()
            # target_description = input("Enter a description of the target person: ").strip()
            # username = input("Enter username of the target person (with or without @): ").strip()
            if username.lower() in ['quit', 'exit']:
                return
            if not username:
                print("Please enter a valid username")
                return

            # Choose AI provider (default Gemini, option for OpenAI in future)
            ai_provider = 'gemini'  # Change to 'openai' for OpenAI support

            if ai_provider == 'gemini':
                initial_message = self.generate_intro_gemini(product_summary, target_description)
            else:
                initial_message = self.generate_intro_openai(product_summary, target_description)

            print(f"\nGenerated intro message:\n{initial_message}\n")
            print(f"Sending message to @{username.lstrip('@')}...")
            success = await self.send_message(username, initial_message)
            if success:
                print("✅ Message sent successfully!")
            else:
                print("❌ Failed to send message")
                return

            print(f"Waiting for a reply from @{username.lstrip('@')}...")
            event_future = asyncio.get_event_loop().create_future()

            @self.client.on(events.NewMessage(from_users=username.lstrip('@'), incoming=True))
            async def reply_handler(event):
                if not event.is_private:
                    return
                if not event_future.done():
                    event_future.set_result(event)

            try:
                event = await asyncio.wait_for(event_future, timeout=300)  # 5 min timeout
                sender = await event.get_sender()
                sender_name = sender.username or sender.first_name or 'Unknown'
                user_reply = event.text
                print(f"\n📩 Reply from @{sender_name}: {user_reply}")

                ai_provider = 'gemini'
                if ai_provider == 'gemini':
                    followup_message = self.generate_reply_gemini(product_summary, target_description, user_reply)
                else:
                    followup_message = "Thanks for your reply! Would you be open to a quick chat with the founder?"

                print(f"\nGenerated follow-up message:\n{followup_message}\n")
                print(f"Sending follow-up message to @{username.lstrip('@')}...")
                success = await self.send_message(username, followup_message)
                if success:
                    print("✅ Follow-up message sent successfully!")
                else:
                    print("❌ Failed to send follow-up message")
            except asyncio.TimeoutError:
                print("No reply received within 5 minutes.")
            finally:
                self.client.remove_event_handler(reply_handler)

            # Automated chat loop using Gemini
            print(f"\nAutomated chat with @{username.lstrip('@')} using Gemini. Conversation will end if the target agrees to meet the founder.")
            chat_history = []
            last_user_reply = None
            while True:
                print(f"Waiting for a reply from @{username.lstrip('@')}...")
                event_future = asyncio.get_event_loop().create_future()

                @self.client.on(events.NewMessage(from_users=username.lstrip('@'), incoming=True))
                async def reply_handler(event):
                    if not event.is_private:
                        return
                    if not event_future.done():
                        event_future.set_result(event)

                try:
                    event = await asyncio.wait_for(event_future, timeout=300)  # 5 min timeout
                    sender = await event.get_sender()
                    sender_name = sender.username or sender.first_name or 'Unknown'
                    last_user_reply = event.text
                    print(f"\n📩 Reply from @{sender_name}: {last_user_reply}")
                    chat_history.append({"role": "user", "name": sender_name, "text": last_user_reply})
                except asyncio.TimeoutError:
                    print("No reply received within 5 minutes. Ending conversation.")
                    self.client.remove_event_handler(reply_handler)
                    break
                finally:
                    self.client.remove_event_handler(reply_handler)

                ai_provider = 'gemini'
                followup_message = self.generate_reply_gemini(product_summary, target_description, last_user_reply, chat_history)
                print(f"\nGenerated message:\n{followup_message}\n")
                chat_history.append({"role": "agent", "name": "Gemini", "text": followup_message})
                print(f"Sending message to @{username.lstrip('@')}...")
                success = await self.send_message(username, followup_message)
                if success:
                    print("✅ Message sent successfully!")
                else:
                    print("❌ Failed to send message")
                    break

                status = self.check_conversation_status_gemini(product_summary, target_description, chat_history)
                if status == "AGREED":
                    print("\n🎉 Target person agreed to meet the founder! Conversation closed.")
                    break
                elif status == "DISAGREED":
                    print("\n❌ Target person declined to meet the founder. Conversation closed.")
                    break
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            print(f"Error: {e}")


async def main(product_summary, target_description, tg_id):
    """Main function to handle command line arguments and run the appropriate mode."""    
    # Initialize sender
    try:
        sender = TelegramSender()
        await sender.connect()
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return 1
    
    try:
        # Interactive mode
        await sender.interactive_mode(product_summary, target_description, tg_id)
    
    finally:
        await sender.disconnect()
    
    return 0

def run_telegram_agent(product_summary, target_description, tg_id):
    try:
        # Schedule the async main function in the current event loop (fire and forget)
        loop = asyncio.get_event_loop()
        loop.create_task(main(product_summary, target_description, tg_id))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")