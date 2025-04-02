#!/usr/bin/env python3
"""
Service for managing user data storage and retrieval.
"""

import logging
from typing import Dict, List, Optional, Any

from models.user import User
from telegram import User as TelegramUser

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user data and state."""

    def __init__(self) -> None:
        """Initialize the user service with an empty user store."""
        self.users: Dict[int, User] = {}
    
    def create_user(self, telegram_user: TelegramUser) -> User:
        """
        Create a new user from a Telegram user object.
        
        Args:
            telegram_user: The Telegram user object
            
        Returns:
            Newly created User object
        """
        user_id = telegram_user.id
        
        user = User(
            id=user_id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            language_code=getattr(telegram_user, 'language_code', None),
            is_bot=telegram_user.is_bot
        )
        self.users[user_id] = user
        logger.info(f"Created new user with ID: {user_id}, name: {user.full_name}")
        
        return user
    
    def get_or_create_user(self, telegram_user: TelegramUser) -> User:
        """
        Get an existing user or create a new one if not exists.
        
        Args:
            telegram_user: The Telegram user object
            
        Returns:
            User object for the given Telegram user
        """
        user_id = telegram_user.id
        
        # Try to get existing user
        user = self.get_user(user_id)
        
        if user is None:
            # Create new user if not found
            user = self.create_user(telegram_user)
        else:
            # Update existing user's Telegram data
            user.update_from_telegram(telegram_user)
            
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            User object if found, None otherwise
        """
        return self.users.get(user_id)
    
    def update_user_data(self, user_id: int, new_data: Dict[str, str]) -> Optional[User]:
        """
        Update user data with new information.
        
        Args:
            user_id: The Telegram user ID
            new_data: Dictionary containing new user data to update
            
        Returns:
            Updated User object if found, None otherwise
        """
        user = self.get_user(user_id)
        if not user:
            logger.warning(f"Attempted to update non-existent user with ID: {user_id}")
            return None
            
        # Update user fields if provided
        if 'name' in new_data and new_data['name']:
            user.final_name = new_data['name']
            
        if 'city' in new_data and new_data['city']:
            user.final_city = new_data['city']
            
        if 'address' in new_data and new_data['address']:
            user.final_address = new_data['address']
            
        logger.debug(f"Updated user {user_id} data: {new_data}")
        return user
    
    def add_message(self, user_id: int, message_text: str, is_from_user: bool = True) -> bool:
        """
        Add a message to the user's conversation history.
        
        Args:
            user_id: The Telegram user ID
            message_text: The text of the message
            is_from_user: Whether the message is from the user (True) or the bot (False)
            
        Returns:
            True if successful, False if user not found
        """
        user = self.get_user(user_id)
        if not user:
            logger.warning(f"Attempted to add message to non-existent user with ID: {user_id}")
            return False
            
        user.add_message(message_text, is_from_user)
        return True
    
    def get_conversation_context(self, user_id: int, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Get the conversation context for a user.
        
        Args:
            user_id: The Telegram user ID
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        user = self.get_user(user_id)
        if not user:
            return []
            
        return user.get_conversation_context(max_messages)
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user from the store.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            True if user was deleted, False if not found
        """
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"Deleted user with ID: {user_id}")
            return True
        return False
    
    def has_all_information(self, user_id: int) -> bool:
        """
        Check if all required information is present for the user.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            True if all required fields have values, False otherwise
        """
        user = self.get_user(user_id)
        if not user:
            return False
            
        return user.is_configured
    
    def get_missing_fields(self, user_id: int) -> List[str]:
        """
        Get a list of missing fields for the user.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            List of field names that are missing values
        """
        user = self.get_user(user_id)
        if not user:
            return ["name", "city", "address"]
            
        return user.get_missing_fields()
    
    def format_for_backend(self, user_id: int) -> str:
        """
        Format user data for the backend.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            Formatted string with XML tags containing user data
        """
        user = self.get_user(user_id)
        if not user:
            return ""
            
        formatted_data = ""
        if user.final_name:
            formatted_data += f"<user_name>{user.final_name}</user_name>\n"
        if user.final_city:
            formatted_data += f"<user_city>{user.final_city}</user_city>\n"
        if user.final_address:
            formatted_data += f"<user_address>{user.final_address}</user_address>"
            
        return formatted_data 