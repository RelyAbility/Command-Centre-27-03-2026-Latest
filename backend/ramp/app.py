"""
RAMP Application Factory
========================

Creates and configures the RAMP application with all services.
"""

from typing import Optional
import logging

from .events.bus import EventBus
from .events.handlers import EventHandlers
from .services.ingestion import IngestionService
from .services.baseline import BaselineEngine
from .services.state import StateEngine
from .services.priority import PriorityEngine
from .services.intervention import InterventionService
from .services.verification import VerificationEngine
from .services.learning import LearningEngine

logger = logging.getLogger(__name__)


class RAMPApplication:
    """
    RAMP Application container.
    
    Holds all services and manages their lifecycle.
    """
    
    def __init__(self, db):
        """
        Initialize RAMP with database connection.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        
        # Create event bus
        self.event_bus = EventBus(db)
        
        # Create services
        self.ingestion = IngestionService(db, self.event_bus)
        self.baseline = BaselineEngine(db, self.event_bus)
        self.state = StateEngine(db, self.event_bus, self.baseline)
        self.priority = PriorityEngine(db, self.event_bus)
        self.intervention = InterventionService(db, self.event_bus)
        self.verification = VerificationEngine(db, self.event_bus)
        self.learning = LearningEngine(db, self.event_bus)
        
        # Create event handlers
        self.handlers = EventHandlers(
            event_bus=self.event_bus,
            baseline_engine=self.baseline,
            state_engine=self.state,
            priority_engine=self.priority,
            verification_engine=self.verification,
            learning_engine=self.learning
        )
        
        # Register handlers
        self.handlers.register_all()
        
        logger.info("RAMP application initialized")
    
    async def start(self):
        """Start the application (event processing)."""
        # Start event processing in background
        # Note: In production, this would be managed differently
        logger.info("RAMP application started")
    
    async def stop(self):
        """Stop the application."""
        await self.event_bus.stop_processing()
        logger.info("RAMP application stopped")


# Singleton instance
_app: Optional[RAMPApplication] = None


def get_ramp_app(db) -> RAMPApplication:
    """
    Get or create the RAMP application instance.
    
    Args:
        db: MongoDB database instance
        
    Returns:
        RAMPApplication instance
    """
    global _app
    if _app is None:
        _app = RAMPApplication(db)
    return _app
