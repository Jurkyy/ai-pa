import aiosmtplib
import imaplib
import email
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from .base import BaseIntegration

class EmailIntegration(BaseIntegration):
    """Email integration using IMAP and SMTP"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.imap = None
        self.smtp = None

    async def initialize(self) -> None:
        """Initialize email connections"""
        self.imap = imaplib.IMAP4_SSL(self.config.get('imap_server'))
        self.smtp = aiosmtplib.SMTP(
            hostname=self.config.get('smtp_server'),
            port=self.config.get('smtp_port', 587),
            use_tls=True
        )
        self.initialized = True

    async def connect(self) -> bool:
        """Connect to email servers"""
        try:
            self.imap.login(
                self.config.get('email'),
                self.config.get('password')
            )
            await self.smtp.connect()
            await self.smtp.login(
                self.config.get('email'),
                self.config.get('password')
            )
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from email servers"""
        if self.imap:
            self.imap.logout()
        if self.smtp:
            await self.smtp.quit()

    async def get_status(self) -> Dict[str, Any]:
        """Get email connection status"""
        return {
            "connected": self.is_connected,
            "email": self.config.get('email'),
            "imap_server": self.config.get('imap_server'),
            "smtp_server": self.config.get('smtp_server')
        }

    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming email events"""
        # Implementation for handling email events
        pass

    async def send_message(self, message: str, to: str, subject: str, **kwargs) -> bool:
        """Send an email"""
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.config.get('email')
            msg['To'] = to

            await self.smtp.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    async def get_messages(self, folder: str = "INBOX", limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Retrieve emails from specified folder"""
        try:
            self.imap.select(folder)
            _, message_numbers = self.imap.search(None, 'ALL')
            messages = []
            
            for num in message_numbers[0].split()[:limit]:
                _, msg_data = self.imap.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                messages.append({
                    'subject': email_message['subject'],
                    'from': email_message['from'],
                    'date': email_message['date'],
                    'body': self._get_email_body(email_message)
                })
            
            return messages
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

    def _get_email_body(self, email_message) -> str:
        """Extract email body from message"""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return email_message.get_payload(decode=True).decode() 