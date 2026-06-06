import os
os.environ["MONGO_URI"] = "not-a-valid-uri"
from forward_bot.config import Settings
s = Settings()
print(f"Loaded MongoDB URI: {s.mongo_uri}")

try:
    import motor.motor_asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(s.mongo_uri)
    print("Motor client created successfully")
except Exception as e:
    print(f"Error creating Motor client: {type(e).__name__}: {e}")
