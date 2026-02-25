from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.faq import router as faq_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router

__all__ = [
    "admin_router",
    "chat_router",
    "faq_router",
    "feedback_router",
    "health_router",
    "knowledge_router",
]
