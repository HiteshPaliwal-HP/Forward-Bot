import asyncio
import sys
from pathlib import Path

# Add src folder to sys.path so we can import forward_bot
sys.path.insert(0, str(Path(__file__).parent / "src"))

from forward_bot.config import Settings
from forward_bot.infrastructure.mongo import mongo_client

async def test_connection():
    print("=== MongoDB Connection Tester ===")
    
    # Check if .env exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("[ERROR] .env file not found!")
        print("Please copy .env.example to .env and configure your variables first:")
        print("  Copy-Item .env.example .env")
        return

    print("1. Loading settings from .env...")
    try:
        settings = Settings()
        # Obfuscate credentials when printing the URI
        obfuscated_uri = settings.mongo_uri
        if "@" in obfuscated_uri:
            parts = obfuscated_uri.split("@")
            prefix = parts[0].split("://")
            scheme = prefix[0]
            obfuscated_uri = f"{scheme}://****:****@{parts[1]}"
        print(f"   Loaded MONGO_URI: {obfuscated_uri}")
    except Exception as e:
        print(f"[ERROR] Loading configuration settings: {e}")
        return

    print("2. Connecting to MongoDB client...")
    try:
        await mongo_client.connect(settings)
        print("   Client initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Connecting client: {e}")
        return

    print("3. Pinging database to test connection...")
    try:
        # Ping the DB to test actual connection
        await mongo_client.db.command("ping")
        print("   Database ping was successful!")
        print("SUCCESS: Your MongoDB connection is working and fully configured.")
    except Exception as e:
        print(f"[ERROR] Database ping failed: {e}")
    finally:
        mongo_client.close()
        print("4. Closed MongoDB connection client.")

if __name__ == "__main__":
    asyncio.run(test_connection())
