#!/usr/bin/env python3
"""
Service for interacting with OpenAI's API to extract user information.
"""


import os
import logging
from typing import Dict, Optional, List, Any, Tuple, cast, TYPE_CHECKING

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

if TYPE_CHECKING:
    from models.user import User

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI API to extract user information."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the OpenAI service.
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        env_api_key = os.getenv("OPENAI_API_KEY", "")
        self.api_key: str = api_key if api_key is not None else env_api_key
        self.client: OpenAI = OpenAI(api_key=self.api_key)
        
    def _create_messages_from_context(self, system_message: ChatCompletionSystemMessageParam, conversation_context: List[Dict[str, Any]], current_message: Optional[str] = None) -> List[ChatCompletionMessageParam]:
        """
        Создает список сообщений из контекста беседы и текущего сообщения.
        
        Args:
            system_message: Системное сообщение
            conversation_context: Контекст беседы
            current_message: Текущее сообщение пользователя (опционально)
            
        Returns:
            Список сообщений для отправки в OpenAI API
        """
        # Строим список сообщений
        messages: List[ChatCompletionMessageParam] = [system_message]
        
        # Добавляем контекст беседы
        if conversation_context:
            for msg in conversation_context:
                if msg["role"] == "user":
                    user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": str(msg["content"])}
                    messages.append(user_msg)
                elif msg["role"] == "assistant":
                    assistant_msg: ChatCompletionMessageParam = {"role": "assistant", "content": str(msg["content"])}
                    messages.append(assistant_msg)
        
        # Добавляем текущее сообщение пользователя, если оно предоставлено
        if current_message:
            user_message: ChatCompletionUserMessageParam = {"role": "user", "content": current_message}
            messages.append(user_message)
            
        return messages
    
    def _call_openai_api(self, messages: List[ChatCompletionMessageParam]) -> str:
        """
        Вызывает OpenAI API и получает ответ.
        
        Args:
            messages: Список сообщений для отправки
            
        Returns:
            Ответ от OpenAI API
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            
            ai_response: str = str(response.choices[0].message.content)
            logger.debug(f"OpenAI response: {ai_response}")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Ошибка при вызове OpenAI API: {e}")
            raise ValueError(f"Не удалось получить ответ от OpenAI: {e}")

    def get_user_info_from_context(self, conversation_context: List[Dict[str, Any]], user: 'User') -> Dict[str, str]:
        """
        Анализирует контекст переписки и извлекает информацию пользователя в XML формате.
        Возвращает только информацию, которую можно уверенно определить из контекста.
        
        Args:
            conversation_context: История переписки с пользователем
            user: Объект пользователя (обязательный)
            
        Returns:
            Dict содержащий извлеченную информацию с ключами 'name', 'city', 'address'
        """
        if user is None:
            logger.error("Ошибка: объект User не предоставлен в get_user_info_from_context")
            raise ValueError("Объект User обязателен для get_user_info_from_context")
        
        # Создаем системное сообщение с учетом уже известной информации
        system_prompt = self._create_system_prompt_for_extraction(user)
        
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system", 
            "content": system_prompt
        }
        
        # Создаем сообщения из контекста
        messages = self._create_messages_from_context(system_message, conversation_context)
        
        try:
            # Вызываем OpenAI API
            ai_response = self._call_openai_api(messages)
            
            # Парсим ответ
            return self._parse_ai_response(ai_response)
        except Exception as e:
            logger.error(f"Ошибка при извлечении информации: {e}")
            return {}
    
    def _create_system_prompt_for_extraction(self, user: 'User') -> str:
        """
        Создает системный промпт для извлечения информации о пользователе.
        
        Args:
            user: Объект пользователя с данными
            
        Returns:
            Строка системного промпта
        """
        system_prompt = (
            "Ты - помощник, созданный для извлечения информации о пользователе. "
            "Извлеки имя пользователя, город и адрес, если они присутствуют в сообщении или контексте. "
        )
        
        # Добавляем информацию о том, что уже известно
        filled_info = []
        if user.final_name:
            filled_info.append(f"имя пользователя: {user.final_name}")
        if user.final_city:
            filled_info.append(f"город: {user.final_city}")
        if user.final_address:
            filled_info.append(f"адрес: {user.final_address}")
        
        if filled_info:
            system_prompt += f"Уже известная информация: {', '.join(filled_info)}. "
            system_prompt += "Не нужно извлекать уже известные поля, если они не изменились. "
        
        system_prompt += (
            "Если ты определил какие-либо из этих данных, добавь их в свой ответ в виде xml-тегов: "
            "<user_name>Имя</user_name>\n"
            "<user_city>Город</user_city>\n"
            "<user_address>Адрес</user_address>\n\n"
            "Включай теги ТОЛЬКО для той информации, которую можешь уверенно извлечь. "
            "Если какой-либо информации нет или она неоднозначна, не включай соответствующий тег."
            "В твоем ответе должны быть только xml-теги и только те что были написаны в списке выше."
            "Это сообщение преднозначено для парсинга программой, поэтому твой ответ должен быть в формате xml."
        )
        
        return system_prompt
    
    def process_user_message(self, message_text: str, conversation_context: List[Dict[str, Any]], user: 'User') -> str:
        """
        Обрабатывает сообщение пользователя и генерирует ответ, учитывая контекст и данные пользователя.
        
        Args:
            message_text: Текст сообщения для обработки
            conversation_context: Предыдущий контекст разговора
            user: Объект пользователя с данными (обязательный)
            
        Returns:
            Сообщение-ответ пользователю
        """
        if user is None:
            logger.error("Ошибка: объект User не предоставлен в process_user_message")
            raise ValueError("Объект User обязателен для process_user_message")
        
        # Получаем пропущенные и заполненные поля
        missing_fields = user.get_missing_fields()
        filled_fields = user.get_filled_fields()
        
        # Создаем системное сообщение
        system_message = self._create_system_message_for_conversation(missing_fields, filled_fields)
        
        # Создаем сообщения из контекста
        messages = self._create_messages_from_context(system_message, conversation_context, message_text)
        
        try:
            # Вызываем OpenAI API
            ai_response = self._call_openai_api(messages)
            return ai_response
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return "Извините, произошла ошибка при обработке вашего сообщения. Пожалуйста, повторите попытку позже."
    
    def _create_system_message_for_conversation(self, missing_fields: List[str], filled_fields: Dict[str, str]) -> ChatCompletionSystemMessageParam:
        """
        Создает системное сообщение для обработки диалога с пользователем.
        
        Args:
            missing_fields: Список отсутствующих полей
            filled_fields: Словарь с заполненными полями
            
        Returns:
            Системное сообщение для OpenAI
        """
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system", 
            "content": (
                "Ты - дружелюбный помощник компании по доставке мороженого. "
                f"Недостающие данные для оформления заказа: {missing_fields}. "
                f"Уже заполненные данные: {filled_fields}. "
                "У тебя две задачи:\n"
                "1. Ответить на вопросы пользователя вежливо и информативно.\n"
                "2. Направить диалог в сторону получения недостающих данных для заказа. "
                "Нужно чтобы пользователь предоставил недостающие данные.\n\n"
                "Если пользователь задает вопрос вместо предоставления информации, "
                "отвечай на его вопрос дружелюбно, но посторайся направить разговор в сторону получения недостающих данных. "
                "Наша компания занимается доставкой мороженого посылками, "
                "Мы отправляем мороженное с северного полюса,"
                "Пользователь заказал 10 коробок эскимо."
                "Если доставка будет долгой, то нужно предупредить пользователя, что мороженое может растаять."
                "Отвечай так, будто ты живой человек, а не бот. Сохраняй непринужденный, "
                "разговорный стиль общения, используй эмодзи для оживления диалога. "
                "Давай краткие, но дружелюбные ответы."
                "Директор завода - Терехов Александр Валерьевич, его почта redmoon.thebest@gmail.com"
                "На производстве работают эльфы, в свободное время они играют в шахматы и читают книги."
            )
        }
        return system_message
        
    def _parse_ai_response(self, ai_response: str) -> Dict[str, str]:
        """
        Parse the OpenAI response to extract structured information.
        
        Args:
            ai_response: Response text from OpenAI
            
        Returns:
            Dictionary with extracted user information
        """
        data: Dict[str, str] = {}
        
        if "<user_name>" in ai_response:
            data["name"] = ai_response.split("<user_name>")[1].split("</user_name>")[0]
            
        if "<user_city>" in ai_response:
            data["city"] = ai_response.split("<user_city>")[1].split("</user_city>")[0]
            
        if "<user_address>" in ai_response:
            data["address"] = ai_response.split("<user_address>")[1].split("</user_address>")[0]
        
        return data 