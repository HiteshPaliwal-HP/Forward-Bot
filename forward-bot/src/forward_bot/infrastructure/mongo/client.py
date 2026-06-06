"""MongoDB connection client using Motor."""
from motor.motor_asyncio import AsyncIOMotorClient
from forward_bot.config import Settings


class MongoClientHolder:
    """Holder for the MongoDB async client and database reference."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db = None

    async def connect(self, settings: Settings) -> None:
        """Initialize the MongoDB client and select the database."""
        self.client = AsyncIOMotorClient(
            settings.mongo_uri,
            # Motor defaults are already sufficient for this scale
        )
        # Parse database name from MONGO_URI
        # Format: mongodb://host:port/database_name?options
        from urllib.parse import urlparse
        
        parsed = urlparse(settings.mongo_uri)
        db_name = parsed.path.strip("/")
        if not db_name:
            db_name = "forward_bot"
            
        self.db = self.client[db_name]

    def close(self) -> None:
        """Close the MongoDB client connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None


# Global singleton instance
mongo_client = MongoClientHolder()
