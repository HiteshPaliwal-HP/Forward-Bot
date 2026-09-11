import asyncio
import sys
from pathlib import Path

# Add src folder to sys.path so we can import forward_bot
sys.path.insert(0, str(Path(__file__).parent / "src"))

from forward_bot.config import Settings
from forward_bot.infrastructure.mongo import mongo_client

async def list_databases_and_collections():
    print("=== MongoDB Database Lister ===")
    settings = Settings()
    await mongo_client.connect(settings)
    
    try:
        # Get list of databases
        dbs = await mongo_client.client.list_database_names()
        print(f"Databases found: {dbs}\n")
        
        for db_name in dbs:
            if db_name in ["admin", "local", "config"]:
                continue
            db = mongo_client.client[db_name]
            collections = await db.list_collection_names()
            print(f"Database: '{db_name}'")
            print(f"Collections: {collections}")
            
            for col_name in collections:
                count = await db[col_name].count_documents({})
                print(f"  - Collection '{col_name}': {count} documents")
            print()
            
    except Exception as e:
        print(f"[ERROR] Listing databases: {e}")
    finally:
        mongo_client.close()

if __name__ == "__main__":
    asyncio.run(list_databases_and_collections())
