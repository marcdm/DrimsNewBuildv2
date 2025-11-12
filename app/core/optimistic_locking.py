"""
Optimistic Locking Implementation for DRIMS
Uses version_nbr column to prevent concurrent modification conflicts
"""
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.core.exceptions import OptimisticLockError
import logging

logger = logging.getLogger(__name__)


def setup_optimistic_locking(db):
    """
    Register optimistic locking event listeners on the SQLAlchemy session.
    
    This ensures that all UPDATE operations on tables with version_nbr
    include the version number in the WHERE clause and increment it.
    """
    
    @event.listens_for(Session, "before_flush")
    def enforce_optimistic_lock(session, flush_context, instances):
        """
        Before flush event: Check version_nbr for all dirty objects
        and prepare optimistic locking updates.
        """
        for obj in session.dirty:
            if not hasattr(obj, 'version_nbr'):
                continue
            
            if not session.is_modified(obj):
                continue
            
            state = inspect(obj)
            
            if state.attrs.version_nbr.history.has_changes():
                continue
            
            original_version = obj.version_nbr
            
            if original_version is None:
                logger.warning(
                    f"Object {obj.__class__.__name__} has None version_nbr, skipping optimistic lock"
                )
                continue
            
            obj.version_nbr = original_version + 1
            
            obj._original_version_nbr = original_version
    
    @event.listens_for(Session, "after_flush")
    def verify_optimistic_lock(session, flush_context):
        """
        After flush event: Verify that updates succeeded with correct version.
        If no rows were updated, it means the version was stale.
        """
        for obj in session.identity_map.values():
            if hasattr(obj, '_original_version_nbr'):
                original_version = obj._original_version_nbr
                delattr(obj, '_original_version_nbr')
                
                state = inspect(obj)
                if state.persistent and hasattr(obj, 'version_nbr'):
                    if obj.version_nbr != original_version + 1:
                        logger.error(
                            f"Optimistic lock failed for {obj.__class__.__name__}, "
                            f"expected version {original_version + 1}, got {obj.version_nbr}"
                        )
                        
                        pk_columns = [col.name for col in inspect(obj.__class__).primary_key]
                        record_id = {col: getattr(obj, col) for col in pk_columns}
                        
                        session.rollback()
                        raise OptimisticLockError(
                            obj.__class__.__name__,
                            record_id
                        )
    
    logger.info("Optimistic locking enabled for all tables with version_nbr")
