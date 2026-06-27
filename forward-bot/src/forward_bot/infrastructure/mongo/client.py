"""MongoDB connection client using Motor."""
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from forward_bot.config import Settings


class MongoClientHolder:
    """Holder for the MongoDB async client and database reference."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db = None

    async def connect(self, settings: Settings) -> None:
        """Initialize the MongoDB client and select the database.

        Uses certifi CA bundle for TLS verification, which is required for
        MongoDB Atlas connections on Windows with OpenSSL 3.0+.
        """
        # Use certifi CA bundle to ensure TLS handshake works on all platforms
        # (especially Windows + OpenSSL 3.0 with MongoDB Atlas)
        self.client = AsyncIOMotorClient(
            settings.mongo_uri,
            tlsCAFile=certifi.where(),
        )
        # Parse database name from MONGO_URI
        # Handles both mongodb:// and mongodb+srv:// schemes
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
