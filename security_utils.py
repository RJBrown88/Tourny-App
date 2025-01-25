from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
import base64
import hmac
import hashlib

class SecurityManager:
    def __init__(self):
        load_dotenv()
        
        # Generate or load encryption key
        key_file = '.encryption_key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.key)
        
        self.cipher_suite = Fernet(self.key)
        self.webhook_secret = os.getenv('DISCORD_WEBHOOK_SECRET')

    def encrypt_webhook_url(self, url: str) -> bytes:
        """Encrypt the Discord webhook URL"""
        return self.cipher_suite.encrypt(url.encode())

    def decrypt_webhook_url(self, encrypted_url: bytes) -> str:
        """Decrypt the Discord webhook URL"""
        return self.cipher_suite.decrypt(encrypted_url).decode()

    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for Discord payload"""
        return hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify the HMAC signature of a Discord payload"""
        expected_signature = self.generate_signature(payload)
        return hmac.compare_digest(signature, expected_signature)