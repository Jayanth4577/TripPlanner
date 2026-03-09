"""FastAPI dependency providers for the backend API."""

from app.agents.orchestrator import OrchestratorAgent
from app.config import Settings, get_settings

_orchestrator: OrchestratorAgent | None = None


def get_settings_dependency() -> Settings:
	"""Return cached application settings."""
	return get_settings()


def get_orchestrator() -> OrchestratorAgent:
	"""Return a singleton orchestrator instance."""
	global _orchestrator
	if _orchestrator is None:
		_orchestrator = OrchestratorAgent()
	return _orchestrator
