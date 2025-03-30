"""Main entry point for the bot."""
import asyncio
import logging
from enbot.app import EnBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def main() -> None:
    """Run the bot."""
    bot = EnBot()
    await bot.start()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main()) 