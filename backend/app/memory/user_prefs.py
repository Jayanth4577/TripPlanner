"""
VoyageMind User Preferences Module

Manages user travel preferences, saved favorites, and past trips.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core import get_cache_manager, CacheKeys

logger = logging.getLogger(__name__)


class UserPreferencesManager:
    """
    Manages user preferences and saved data.
    
    Stores:
    - Travel style preferences (budget, pace, activities)
    - Dietary/accessibility requirements
    - Favorite destinations/hotels/airlines
    - Past trips
    """

    def __init__(self):
        """Initialize preferences manager"""
        self.cache = get_cache_manager()
        self.prefs_ttl = 30 * 24 * 60 * 60  # 30 days

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Preferences dictionary
        """
        cache_key = CacheKeys.USER_PREFS.format(user_id=user_id)
        prefs = self.cache.get(cache_key)
        
        if prefs:
            logger.debug(f"Retrieved preferences for user {user_id}")
            return prefs
        
        # Return defaults if not found
        return self._get_default_preferences()

    def set_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Set user preferences.
        
        Args:
            user_id: User ID
            preferences: Preferences dictionary
            
        Returns:
            True if successful
        """
        # Validate preferences
        validated = self._validate_preferences(preferences)
        
        cache_key = CacheKeys.USER_PREFS.format(user_id=user_id)
        success = self.cache.set(cache_key, validated, ttl=self.prefs_ttl)
        
        if success:
            logger.info(f"Updated preferences for user {user_id}")
        
        return success

    def update_preferences(self, user_id: str, **updates) -> bool:
        """
        Update specific preferences without overwriting others.
        
        Args:
            user_id: User ID
            **updates: Preference fields to update
            
        Returns:
            True if successful
        """
        current = self.get_preferences(user_id)
        current.update(updates)
        return self.set_preferences(user_id, current)

    def add_favorite_destination(self, user_id: str, destination: str) -> bool:
        """
        Add a favorite destination.
        
        Args:
            user_id: User ID
            destination: Destination name
            
        Returns:
            True if successful
        """
        prefs = self.get_preferences(user_id)
        
        if "favorite_destinations" not in prefs:
            prefs["favorite_destinations"] = []
        
        if destination not in prefs["favorite_destinations"]:
            prefs["favorite_destinations"].append(destination)
        
        return self.set_preferences(user_id, prefs)

    def add_favorite_hotel(self, user_id: str, hotel_id: str, hotel_name: str) -> bool:
        """
        Add a favorite hotel.
        
        Args:
            user_id: User ID
            hotel_id: Hotel ID
            hotel_name: Hotel name
            
        Returns:
            True if successful
        """
        prefs = self.get_preferences(user_id)
        
        if "favorite_hotels" not in prefs:
            prefs["favorite_hotels"] = {}
        
        prefs["favorite_hotels"][hotel_id] = hotel_name
        
        return self.set_preferences(user_id, prefs)

    def add_favorite_airline(self, user_id: str, airline_code: str, airline_name: str) -> bool:
        """
        Add a favorite airline.
        
        Args:
            user_id: User ID
            airline_code: Airline IATA code
            airline_name: Airline name
            
        Returns:
            True if successful
        """
        prefs = self.get_preferences(user_id)
        
        if "favorite_airlines" not in prefs:
            prefs["favorite_airlines"] = {}
        
        prefs["favorite_airlines"][airline_code] = airline_name
        
        return self.set_preferences(user_id, prefs)

    def set_dietary_restrictions(self, user_id: str, restrictions: List[str]) -> bool:
        """
        Set dietary restrictions.
        
        Args:
            user_id: User ID
            restrictions: List of dietary restrictions
            
        Returns:
            True if successful
        """
        return self.update_preferences(user_id, dietary_restrictions=restrictions)

    def set_accessibility_needs(self, user_id: str, needs: List[str]) -> bool:
        """
        Set accessibility requirements.
        
        Args:
            user_id: User ID
            needs: List of accessibility needs
            
        Returns:
            True if successful
        """
        return self.update_preferences(user_id, accessibility_needs=needs)

    def set_travel_style(
        self,
        user_id: str,
        pace: str = "moderate",  # relaxed, moderate, fast
        budget_preference: str = "balanced",  # budget, balanced, luxury
        accommodation_type: str = "hotel",  # hotel, hostel, airbnb, resort
    ) -> bool:
        """
        Set user's travel style.
        
        Args:
            user_id: User ID
            pace: Travel pace preference
            budget_preference: Budget preference
            accommodation_type: Preferred accommodation type
            
        Returns:
            True if successful
        """
        return self.update_preferences(
            user_id,
            travel_style={
                "pace": pace,
                "budget_preference": budget_preference,
                "accommodation_type": accommodation_type,
            }
        )

    def _get_default_preferences(self) -> Dict[str, Any]:
        """
        Get default user preferences.
        
        Returns:
            Default preferences dictionary
        """
        return {
            "travel_style": {
                "pace": "moderate",
                "budget_preference": "balanced",
                "accommodation_type": "hotel",
            },
            "dietary_restrictions": [],
            "accessibility_needs": [],
            "favorite_destinations": [],
            "favorite_hotels": {},
            "favorite_airlines": {},
            "language": "en",
            "currency": "USD",
            "notifications_enabled": True,
            "save_history": True,
        }

    def _validate_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean preferences.
        
        Args:
            preferences: Preferences to validate
            
        Returns:
            Validated preferences
        """
        # Ensure required keys exist
        defaults = self._get_default_preferences()
        
        for key, value in defaults.items():
            if key not in preferences:
                preferences[key] = value
        
        # Validate specific fields
        if "travel_style" in preferences:
            valid_paces = ["relaxed", "moderate", "fast"]
            if preferences["travel_style"].get("pace") not in valid_paces:
                preferences["travel_style"]["pace"] = "moderate"
            
            valid_budgets = ["budget", "balanced", "luxury"]
            if preferences["travel_style"].get("budget_preference") not in valid_budgets:
                preferences["travel_style"]["budget_preference"] = "balanced"
        
        return preferences


# Singleton instance
_prefs_manager: Optional[UserPreferencesManager] = None


def get_user_preferences_manager() -> UserPreferencesManager:
    """
    Get or create user preferences manager instance (singleton).
    
    Returns:
        UserPreferencesManager instance
    """
    global _prefs_manager
    if _prefs_manager is None:
        _prefs_manager = UserPreferencesManager()
    return _prefs_manager
