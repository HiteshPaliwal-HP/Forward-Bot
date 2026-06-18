"""FastAPI dependencies for injecting services and repositories."""
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends

from forward_bot.infrastructure.mongo import mongo_client
from forward_bot.infrastructure.telegram import telegram_client, TelegramClientHolder
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository
from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository


def get_db() -> AsyncIOMotorDatabase:
    """Injects the active MongoDB database reference."""
    if mongo_client.db is None:
        raise RuntimeError("MongoDB database reference is not initialized.")
    return mongo_client.db


def get_source_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> SourceRepository:
    """Injects the SourceRepository."""
    return SourceRepository(db)


def get_folder_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> FolderRepository:
    """Injects the FolderRepository."""
    return FolderRepository(db)


def get_rule_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> ForwardingRuleRepository:
    """Injects the ForwardingRuleRepository."""
    return ForwardingRuleRepository(db)


def get_replacement_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> ReplacementRuleRepository:
    """Injects the ReplacementRuleRepository."""
    return ReplacementRuleRepository(db)


def get_telegram_client() -> TelegramClientHolder:
    """Injects the TelegramClientHolder connection client."""
    return telegram_client

