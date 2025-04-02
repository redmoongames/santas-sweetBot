#!/usr/bin/env python3
"""
Service for message handling and conversation flow coordination.
"""

import logging

from models.user import User
from services.user_service import UserService
from services.openai_service import OpenAIService
from services.backend_service import BackendService

logger = logging.getLogger(__name__)


class MessageService:
    """
    Central service for handling messages and coordinating conversation flow.
    This service receives user messages, processes them, saves conversation history,
    and determines the appropriate response and next steps.
    """
    
    def __init__(self, user_service, openai_service, backend_service) -> None:
        """
        Initialize the message service with required dependencies.
        
        Args:
            user_service: Service for user data management
            openai_service: Service for OpenAI interactions
            backend_service: Service for backend interactions
        """
        self.user_service: UserService = user_service
        self.openai_service: OpenAIService = openai_service
        self.backend_service: BackendService = backend_service
    
    def get_welcome_message(self) -> str:
        """
        Get the welcome message for a user.
            
        Returns:
            Welcome message text
        """
        return (
            "Привет! 👋 Спасибо за заказ в нашем магазине мороженого! 🍦\n\n"
            "Меня зовут Мороженка, и я помогу вам оформить доставку самого вкусного мороженого до вашей двери! ❄️\n\n"
            "Чтобы отправить вам заказ, мне нужно знать:\n"
            "1. Ваше имя 📝\n"
            "2. Город доставки 🏙️\n"
            "3. Адрес доставки 🏠\n\n"
            "Пожалуйста, напишите эту информацию в любой удобной форме. Также я с радостью отвечу на любые вопросы о доставке или нашем мороженом! 😊\n\n"
            "P.S. Обратите внимание, что мы отправляем мороженое в специальной термоупаковке, но всё же есть небольшой риск, что оно может немного подтаять при доставке в жаркую погоду. Но не переживайте, вкус от этого не пострадает! 🌡️"
        )
        
    def process_user_message(self, user_id: int, message_text: str) -> str:
        """
        Process a user message and determine the appropriate response.
        This is the main entry point for message handling.
        
        Args:
            user_id: The Telegram user ID
            message_text: The message text from the user
            
        Returns:
            Response message to send back to the user
        """
        user = self.user_service.get_user(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return "Ой, на сервере произошла ошибка... Напишите нам в поддержку на redmoon.thebest@gmail.com"
        
        logger.info(f"[FROM {user.id}] {message_text}")
        self.user_service.add_message(user_id, message_text, is_from_user=True)
        
        response = ""
        if user.is_configured:
            response = self._get_complete_info_message(user)
        else:
            response = self._handle_unconfigured_user(user_id, message_text)
            
        logger.info(f"[TO {user.id}] {response}")
        self.user_service.add_message(user_id, response, is_from_user=False)
        
        return response
        
    def _handle_unconfigured_user(self, user_id: int, message_text: str) -> str:
        """
        Handle a message from a user who still needs to provide information.
        
        Args:
            user_id: The Telegram user ID
            message_text: The message text from the user
            
        Returns:
            Response message to send back to the user
        """
        # Получаем контекст разговора
        conversation_context = self.user_service.get_conversation_context(user_id)
        
        # Получаем пользователя
        user = self.user_service.get_user(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return "Ой, на сервере произошла ошибка... Напишите нам в поддержку на redmoon.thebest@gmail.com"
            
        # Извлекаем информацию из всего контекста переписки
        extracted_info = self.openai_service.get_user_info_from_context(conversation_context, user)
        
        # Обновляем данные пользователя, если что-то извлекли
        if extracted_info:
            self.user_service.update_user_data(user_id, extracted_info)
            
            # Получаем обновленного пользователя после обновления данных
            user = self.user_service.get_user(user_id)
            if not user:
                return "Ой, на сервере произошла ошибка... Напишите нам в поддержку на redmoon.thebest@gmail.com"
        
        # Проверяем, полностью ли настроен пользователь после обновления
        if user.is_configured:
            # Пользователь предоставил всю необходимую информацию
            backend_data = self.user_service.format_for_backend(user_id)
            self.backend_service.send_user_data(backend_data)
            
            # Возвращаем сообщение с полной информацией
            return self._get_complete_info_message(user)
        
        # Генерируем ответ пользователю
        response = self.openai_service.process_user_message(
            message_text=message_text,
            conversation_context=conversation_context,
            user=user
        )
        
        return response
    
    def get_cancel_message(self, user_id: int) -> str:
        """
        Get the cancellation message for a user.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            Cancellation message text
        """
        user = self.user_service.get_user(user_id)
        
        if user and user.first_name:
            return (
                f"Жаль, {user.first_name}, что вы решили отменить оформление заказа на мороженое! 🍦\n\n"
                f"Мы удалили ваши данные из системы.\n\n"
                f"Если захотите вернуться и заказать наше восхитительное мороженое, просто напишите /start, и я с радостью помогу вам! ❄️"
            )
            
        return (
            f"Жаль, что вы решили отменить оформление заказа на мороженое! 🍦\n\n"
            f"Мы удалили ваши данные из системы.\n\n"
            f"Если захотите вернуться и заказать наше восхитительное мороженое, просто напишите /start, и я с радостью помогу вам! ❄️"
        )
    
    def _get_missing_info_message(self, user: User) -> str:
        """
        Get a message asking for missing information.
        
        Args:
            user: User object
            
        Returns:
            Message asking for missing information
        """
        missing_fields = user.get_missing_fields()
        missing_str = ", ".join(missing_fields)
        
        # Преобразуем английские имена полей в русские
        field_translations = {
            "name": "имя",
            "city": "город",
            "address": "адрес"
        }
        
        # Создаем список недостающих полей на русском
        missing_ru = []
        for field in missing_fields:
            if field in field_translations:
                missing_ru.append(field_translations[field])
        
        missing_str_ru = ", ".join(missing_ru)
        
        # Если у нас есть имя пользователя, персонализируем сообщение
        if user.first_name:
            return (
                f"Спасибо за информацию, {user.first_name}! 😊\n\n"
                f"Для оформления доставки мороженого мне всё ещё нужно узнать: {missing_str_ru}.\n\n"
                f"Мы отправляем наше мороженое в специальной термоупаковке, чтобы оно оставалось холодным в пути! 🧊"
            )
        
        return (
            f"Спасибо за информацию! 😊\n\n"
            f"Для оформления доставки мороженого мне всё ещё нужно узнать: {missing_str_ru}.\n\n"
            f"Наше мороженое доставляется в специальной холодильной упаковке, но лучше быть дома в момент доставки, чтобы оно не успело растаять. ❄️"
        )
    
    def _get_complete_info_message(self, user: User) -> str:
        """
        Get the message confirming all information has been collected.
        
        Args:
            user: User object
            
        Returns:
            Confirmation message with all user information
        """
        # Make sure to handle None values
        name = user.final_name or ""
        city = user.final_city or ""
        address = user.final_address or ""
        
        return (
            f"Отлично! 🎉 Спасибо за предоставленную информацию, {name}!\n\n"
            f"Ваш заказ будет доставлен по адресу:\n"
            f"🏙️ Город: {city}\n"
            f"🏠 Адрес: {address}\n\n"
            f"Мы уже начали готовить ваше мороженое к отправке! Оно будет упаковано в специальный термоконтейнер, чтобы минимизировать риск таяния. ❄️\n\n"
            f"Если у вас возникнут вопросы о статусе заказа, пожалуйста, используйте команду /restart, чтобы начать новый диалог с нами.\n\n"
            f"Спасибо за выбор нашего мороженого! 🍦\n\n"
            f"P.S. Это задание выполнено в рамках творческой работы для Ковалева Игоря Петровича."
        )
    
    def _get_answer_with_missing_fields(self, user: User, answer: str) -> str:
        """
        Get a message with an answer to the user's question and a reminder about missing fields.
        
        Args:
            user: User object
            answer: Answer to the user's question
            
        Returns:
            Message with answer and missing fields reminder
        """
        missing_fields = user.get_missing_fields()
        if not missing_fields:
            return answer
            
        # Преобразуем английские имена полей в русские
        field_translations = {
            "name": "имя",
            "city": "город",
            "address": "адрес"
        }
        
        # Создаем список недостающих полей на русском
        missing_ru = []
        for field in missing_fields:
            if field in field_translations:
                missing_ru.append(field_translations[field])
        
        missing_str_ru = ", ".join(missing_ru)
            
        return (
            f"{answer}\n\n"
            f"Кстати, для оформления доставки мороженого мне всё ещё нужно: {missing_str_ru}. "
            f"Как только я получу эту информацию, мы сможем отправить ваш заказ! 🍦"
        ) 