#!/usr/bin/env python3
"""
Telegram bot for collecting user information with OpenAI integration.
This is the main entry point that sets up the bot and handlers.
"""

import logging
import os
from typing import Dict, Any, Optional, cast

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from services.openai_service import OpenAIService
from services.user_service import UserService
from services.message_service import MessageService
from services.backend_service import BackendService
from models.user import User

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
COLLECTING_INFO: int = 0

# Initialize services
user_service: UserService = UserService()
openai_service: OpenAIService = OpenAIService()
backend_service: BackendService = BackendService()
message_service: MessageService = MessageService(user_service, openai_service, backend_service)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for user information."""
    if update.effective_user is None or update.message is None:
        logger.error("Received update with no effective user or message")
        return ConversationHandler.END
        
    user_id: int = update.effective_user.id
    telegram_user = update.effective_user
    
    user = user_service.get_or_create_user(telegram_user)
    welcome_message: str = message_service.get_welcome_message()
    await update.message.reply_text(welcome_message)
    
    return COLLECTING_INFO


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Restart the conversation by deleting user data and starting fresh."""
    if update.effective_user is None or update.message is None:
        logger.error("Received update with no effective user or message")
        return ConversationHandler.END
        
    user_id: int = update.effective_user.id
    telegram_user = update.effective_user
    
    # Delete existing user data
    user_service.delete_user(user_id)
    
    # Create new user and start again
    user_service.get_or_create_user(telegram_user)
    
    # Send restart confirmation and welcome message
    restart_message = "Перезапускаем бота... 🔄\n\nВсе данные сброшены! Давайте начнем оформление заказа на мороженое заново! 🍦❄️"
    await update.message.reply_text(restart_message)
    
    # Send welcome message
    welcome_message: str = message_service.get_welcome_message()
    await update.message.reply_text(welcome_message)
    
    return COLLECTING_INFO


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process user messages by delegating to MessageService."""
    if update.effective_user is None or update.message is None:
        logger.error("Received update with no effective user or message")
        return ConversationHandler.END
        
    user_id: int = update.effective_user.id
    
    # Make sure we have text
    message_text = update.message.text
    if message_text is None:
        logger.warning("Received message with no text from user %s", user_id)
        message_text = ""
    
    # Let the message service process the message and determine the response
    response = message_service.process_user_message(user_id, message_text)
    
    # Send the response to the user
    await update.message.reply_text(response)
    
    # Check if user has all required information to decide if we should end the conversation
    if user_service.has_all_information(user_id):
        return ConversationHandler.END
    else:
        return COLLECTING_INFO


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    if update.effective_user is None or update.message is None:
        logger.error("Received update with no effective user or message")
        return ConversationHandler.END
        
    user_id: int = update.effective_user.id
    
    # Delete user or reset data
    user_service.delete_user(user_id)
    
    # Get cancellation message
    cancel_message: str = message_service.get_cancel_message(user_id)
    
    # Send message to user
    await update.message.reply_text(cancel_message)
    
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Get telegram token
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_TOKEN not found in environment variables")
        return
        
    # Create the Application
    application: Application = Application.builder().token(telegram_token).build()

    # Add conversation handler
    conv_handler: ConversationHandler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("restart", restart)
        ],
        states={
            COLLECTING_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                CommandHandler("restart", restart)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main() 