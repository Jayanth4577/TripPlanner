"""
VoyageMind Session Management Module

Handles user sessions, conversation history, and context persistence.
"""

import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.core import get_cache_manager, CacheKeys
from app.models.schemas import SessionData

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions and conversation context.
    
    Responsibilities:
    - Create and retrieve sessions
    - Store conversation history
    - Maintain user context
    - Handle session expiration
    """

    def __init__(self):
        """Initialize session manager"""
        self.cache = get_cache_manager()
        self.session_ttl = 24 * 60 * 60  # 24 hours

    def create_session(self, user_id: str) -> str:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "current_trip": None,
            "conversation_history": [],
            "preferences": {},
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
        }
        
        # Cache session
        cache_key = CacheKeys.SESSION.format(session_id=session_id)
        self.cache.set(cache_key, session_data, ttl=self.session_ttl)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionData or None if not found
        """
        cache_key = CacheKeys.SESSION.format(session_id=session_id)
        data = self.cache.get(cache_key)
        
        if data:
            logger.debug(f"Retrieved session {session_id}")
            return SessionData(**data)
        
        logger.warning(f"Session not found: {session_id}")
        return None

    def update_session(self, session_id: str, **updates) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            **updates: Fields to update
            
        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Convert to dict and update
        session_dict = session.model_dump()
        session_dict.update(updates)
        session_dict["last_accessed_at"] = datetime.utcnow().isoformat()
        
        cache_key = CacheKeys.SESSION.format(session_id=session_id)
        success = self.cache.set(cache_key, session_dict, ttl=self.session_ttl)
        
        if success:
            logger.debug(f"Updated session {session_id}")
        
        return success

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to conversation history.
        
        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            
        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get current history and append
        history = session.conversation_history or []
        history.append(message)
        
        # Keep last 50 messages to avoid memory bloat
        if len(history) > 50:
            history = history[-50:]
        
        return self.update_session(session_id, conversation_history=history)

    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of message dictionaries
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        return session.conversation_history or []

    def set_current_trip(self, session_id: str, trip_id: str) -> bool:
        """
        Set current trip for session.
        
        Args:
            session_id: Session ID
            trip_id: Trip ID
            
        Returns:
            True if successful
        """
        return self.update_session(session_id, current_trip=trip_id)

    def set_preferences(self, session_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Set user preferences in session.
        
        Args:
            session_id: Session ID
            preferences: Preferences dictionary
            
        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Merge with existing preferences
        current_prefs = session.preferences or {}
        current_prefs.update(preferences)
        
        return self.update_session(session_id, preferences=current_prefs)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful
        """
        cache_key = CacheKeys.SESSION.format(session_id=session_id)
        success = self.cache.delete(cache_key)
        
        if success:
            logger.info(f"Deleted session {session_id}")
        
        return success

    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions (automated).
        Redis handles TTL, but this can be called periodically.
        
        Returns:
            Number of sessions cleaned
        """
        # Redis automatically removes expired keys via TTL
        logger.info("Session cleanup: Redis TTL handles expiration automatically")
        return 0


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get or create session manager instance (singleton).
    
    Returns:
        SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
