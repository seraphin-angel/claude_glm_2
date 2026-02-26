from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.faq import router as faq_router
from app.api.feedback import router as feedback_router
from app.api.gdpr import router as gdpr_router
from app.api.health import router as health_router
from app.api.integrations import router as integrations_router
from app.api.knowledge import router as knowledge_router
from app.api.tenant import router as tenant_router

__all__ = [
    "admin_router",
    "chat_router",
    "faq_router",
    "feedback_router",
    "gdpr_router",
    "health_router",
    "integrations_router",
    "knowledge_router",
    "tenant_router",
]
