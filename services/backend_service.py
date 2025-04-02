#!/usr/bin/env python3
"""
Service for handling backend interactions and data parsing.
"""

import logging
import re
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class BackendService:
    """Service for handling backend interactions and data parsing."""
    
    def __init__(self) -> None:
        """Initialize the backend service."""
        pass
    
    def send_user_data(self, formatted_data: str) -> bool:
        """
        Send user data to the backend.
        
        This is a placeholder method that would typically make an API call
        to your backend service. Currently, it just logs the data.
        
        Args:
            formatted_data: Data formatted with XML tags
        
        Returns:
            bool: Success status
        """
        logger.info("Sending to backend: %s", formatted_data)
        return True
    
    def parse_user_data(self, data: str) -> Dict[str, Optional[str]]:
        """
        Parse user data from XML-like format.
        
        Args:
            data: String containing user data in XML format
                <user_name>Name</user_name>
                <user_city>City</user_city>
                <user_address>Address</user_address>
                
        Returns:
            Dictionary with parsed user data
        """
        result: Dict[str, Optional[str]] = {
            "name": None,
            "city": None,
            "address": None
        }
        
        # Extract name
        name_match = re.search(r'<user_name>(.*?)</user_name>', data, re.DOTALL)
        if name_match:
            result["name"] = name_match.group(1).strip()
        
        # Extract city
        city_match = re.search(r'<user_city>(.*?)</user_city>', data, re.DOTALL)
        if city_match:
            result["city"] = city_match.group(1).strip()
        
        # Extract address
        address_match = re.search(r'<user_address>(.*?)</user_address>', data, re.DOTALL)
        if address_match:
            result["address"] = address_match.group(1).strip()
        
        return result 