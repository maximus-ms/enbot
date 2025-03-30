"""Main entry point for the bot."""
import asyncio
import logging
import signal
import sys
from enbot.app import EnBot
from enbot.config import ensure_directories

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def shutdown(signal, loop):
    """Cleanup tasks tied to the service's shutdown."""
    print(f"\nReceived exit signal {signal.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    print(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    
    loop.stop()

def handle_exception(loop, context):
    """Handle exceptions in the event loop."""
    msg = context.get("exception", context["message"])
    print(f"Caught exception: {msg}")
    print("Shutting down...")
    # Don't create a new task here, just stop the loop
    loop.stop()

async def main() -> None:
    """Run the bot."""
    # Ensure all required directories exist
    ensure_directories()
    
    # Get the event loop
    loop = asyncio.get_event_loop()
    
    # Add signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    
    # Set exception handler
    loop.set_exception_handler(handle_exception)
    
    try:
        # Start the bot
        print("Starting bot...")
        bot = EnBot()
        await bot.start()
        
        # Keep the application running
        while True:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
    finally:
        # Cleanup
        print("Cleaning up...")
        await bot.stop()

if __name__ == "__main__":
    try:
        # Create and set event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the main function
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
    finally:
        loop.close() 