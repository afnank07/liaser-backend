import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TelegramConfig:
    """Configuration class for Telegram API credentials and settings."""
    
    def __init__(self):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.phone_number = os.getenv('PHONE_NUMBER')
        self.session_name = os.getenv('SESSION_NAME', 'telegram_session')
        
        # Validate required credentials
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate that all required credentials are provided."""
        missing_credentials = []
        
        if not self.api_id:
            missing_credentials.append('API_ID')
        if not self.api_hash:
            missing_credentials.append('API_HASH')
        if not self.phone_number:
            missing_credentials.append('PHONE_NUMBER')
        
        if missing_credentials:
            raise ValueError(
                f"Missing required credentials: {', '.join(missing_credentials)}\n"
                "Please create a .env file based on .env.example and fill in your credentials."
            )
    
    def get_api_id(self):
        """Get API ID as integer."""
        try:
            return int(self.api_id)
        except (ValueError, TypeError):
            raise ValueError("API_ID must be a valid integer")
    
    def get_api_hash(self):
        """Get API hash."""
        return self.api_hash
    
    def get_phone_number(self):
        """Get phone number."""
        return self.phone_number
    
    def get_session_name(self):
        """Get session name."""
        return self.session_name
