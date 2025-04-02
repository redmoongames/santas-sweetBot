#!/usr/bin/env python3
"""
User model for the Telegram bot.
Stores user information and conversation state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class UserMessage:
    """Message representation for conversation history."""
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_from_user: bool = True


@dataclass
class User:
    """User model with Telegram information and delivery details."""
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_bot: bool = False
    
    final_name: Optional[str] = None
    final_city: Optional[str] = None
    final_address: Optional[str] = None
    
    conversation_history: List[UserMessage] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    
    @property
    def is_configured(self) -> bool:
        """Check if all required fields are configured."""
        return all([self.final_name, self.final_city, self.final_address])
    
    @property
    def full_name(self) -> str:
        """Get the user's full name from Telegram data or configured name."""
        if self.final_name:
            return self.final_name
        
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        
        return self.first_name or self.username or f"User {self.id}"
    
    def add_message(self, text: str, is_from_user: bool = True) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            text: The message text
            is_from_user: Whether the message is from the user (True) or the bot (False)
        """
        message = UserMessage(text=text, is_from_user=is_from_user)
        self.conversation_history.append(message)
        self.last_interaction = datetime.now()
    
    def get_conversation_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Get the conversation context formatted for OpenAI API.
        
        Args:
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        recent_messages = self.conversation_history[-max_messages:] if self.conversation_history else []
        
        context = []
        for message in recent_messages:
            role = "user" if message.is_from_user else "assistant"
            context.append({"role": role, "content": message.text})
            
        return context
    
    def update_from_telegram(self, telegram_user: Any) -> None:
        """
        Update user information from Telegram user object.
        
        Args:
            telegram_user: Telegram user object
        """
        self.username = getattr(telegram_user, 'username', self.username)
        self.first_name = getattr(telegram_user, 'first_name', self.first_name)
        self.last_name = getattr(telegram_user, 'last_name', self.last_name)
        self.language_code = getattr(telegram_user, 'language_code', self.language_code)
        self.is_bot = getattr(telegram_user, 'is_bot', self.is_bot)
        self.last_interaction = datetime.now()
    
    def get_missing_fields(self) -> List[str]:
        """
        Get a list of missing required fields.
        
        Returns:
            List of field names that are not configured
        """
        missing = []
        if not self.final_name:
            missing.append("name")
        if not self.final_city:
            missing.append("city")
        if not self.final_address:
            missing.append("address")
        return missing 
    
    def get_filled_fields(self) -> Dict[str, str]:
        """
        Get a dictionary of filled fields.
        
        Returns:
            Dictionary of filled fields with field names as keys and values as field values
        """ 
        filled = {}
        if self.final_name:
            filled["name"] = self.final_name
        if self.final_city:
            filled["city"] = self.final_city
        if self.final_address:
            filled["address"] = self.final_address
        return filled
