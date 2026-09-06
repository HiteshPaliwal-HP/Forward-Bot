"""
One-time Telegram authentication script.
Run this ONCE on the server to create the session file.
Usage: uv run python auth_telegram.py (from the forward-bot directory)
"""
import asyncio
from telethon import TelegramClient
from forward_bot.config import Settings

async def main():
    settings = Settings()
    session_path = settings.telegram_session_path

    print(f"Creating Telegram session at: {session_path}")
    print("You will be prompted for your phone number and OTP.\n")

    client = TelegramClient(
        str(session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    await client.start()

    me = await client.get_me()
    print(f"\n✅ Successfully authenticated!")
    print(f"Logged in as: {me.first_name} (@{me.username})")
    print(f"Session saved to: {session_path}.session")
    print("\nYou can now start the bot service:")
    print("  sudo systemctl start forward-bot")

    await client.disconnect()

asyncio.run(main())
