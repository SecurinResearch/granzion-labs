"""
Database connection management for Granzion Lab.
Provides SQLAlchemy engine and session management.
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.config import settings
from src.database.models import Base


# Synchronous engine and session factory
sync_engine = create_engine(
    settings.postgres_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


# Asynchronous engine and session factory
async_engine = create_async_engine(
    settings.postgres_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    poolclass=NullPool,  # Use NullPool for async to avoid connection issues
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def init_db() -> None:
    """
    Initialize database schema.
    
    Note: In production, this should be handled by Alembic migrations.
    For the lab, we use SQL init scripts in db/init/ directory.
    """
    logger.info("Initializing database schema...")
    
    try:
        # Create all tables (if they don't exist)
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def check_pgvector_extension() -> bool:
    """
    Check if pgvector extension is installed.
    
    Returns:
        bool: True if pgvector is available, False otherwise
    """
    try:
        with sync_engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            exists = result.scalar()
        
        if exists:
            logger.info("pgvector extension is installed")
        else:
            logger.warning("pgvector extension is NOT installed")
        
        return exists
    except Exception as e:
        logger.error(f"Failed to check pgvector extension: {e}")
        return False


class SessionWrapper:
    """
    Wrapper around SQLAlchemy Session to automatically handle textual SQL.
    Fixes compatibility issues with SQLAlchemy 2.0+ where raw strings are not allowed.
    """
    def __init__(self, session: Session):
        self._session = session
        
    def execute(self, statement, *args, **kwargs):
        # Automatically wrap string statements in text()
        if isinstance(statement, str):
            # Check for legacy %s style with tuple parameters
            # args[0] is the parameters tuple/list
            if '%s' in statement and args and isinstance(args[0], (tuple, list)) and len(args) == 1:
                params_seq = args[0]
                # If distinct parameters (not a list of dicts for executemany)
                if params_seq and not isinstance(params_seq[0], dict):
                    # Replace %s with :p_N
                    parts = statement.split('%s')
                    if len(parts) - 1 == len(params_seq):
                        new_stmt = ""
                        new_params = {}
                        for i, part in enumerate(parts[:-1]):
                            new_stmt += f"{part}:p_{i}"
                            new_params[f"p_{i}"] = params_seq[i]
                        new_stmt += parts[-1]
                        
                        statement = text(new_stmt)
                        return self._session.execute(statement, new_params, **kwargs)
            
            statement = text(statement)
        return self._session.execute(statement, *args, **kwargs)
        
    def __getattr__(self, name):
        return getattr(self._session, name)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a synchronous database session.
    
    Usage:
        with get_db() as db:
            # Use db session
            pass
    
    Yields:
        Session: SQLAlchemy session (wrapped)
    """
    db = SyncSessionLocal()
    try:
        yield SessionWrapper(db)  # type: ignore
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an asynchronous database session.
    
    Usage:
        async with get_async_db() as db:
            # Use db session
            pass
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_dependency():
    """
    FastAPI dependency for database sessions.
    
    Usage in FastAPI:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db_dependency)):
            # Use db session
            pass
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db_dependency():
    """
    FastAPI dependency for async database sessions.
    
    Usage in FastAPI:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_async_db_dependency)):
            # Use db session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Event listeners for connection pool
@event.listens_for(sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new connection is created."""
    logger.debug("New database connection established")


@event.listens_for(sync_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(sync_engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log when a connection is returned to the pool."""
    logger.debug("Connection returned to pool")


def close_db_connections():
    """Close all database connections."""
    logger.info("Closing database connections...")
    sync_engine.dispose()
    logger.info("Database connections closed")


async def close_async_db_connections():
    """Close all async database connections."""
    logger.info("Closing async database connections...")
    await async_engine.dispose()
    logger.info("Async database connections closed")
