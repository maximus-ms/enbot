"""Main entry point for the bot."""
import asyncio
import logging
import signal
import sys
from enbot.app import EnBot
from enbot.config import ensure_directories, settings
from typing import Optional


# Configure logging
def setup_logging(level: Optional[int] = None, dir: Optional[str] = None) -> None:
    """Configure logging for the entire application.
    
    Args:
        level: Optional logging level. If None, defaults to INFO.
        dir: Optional directory for log files. If None, uses default logs directory.
    """
    # Set default level if not provided
    if level is None:
        level = logging.INFO
    elif isinstance(level, str):
        level = logging.getLevelName(level)

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler with rotation
    if dir is not None:
        try:
            from pathlib import Path
            from logging.handlers import TimedRotatingFileHandler
            
            # Use provided directory or default to 'logs'
            log_dir = Path(dir) if dir else Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Create rotating file handler
            log_file = log_dir / "enbot.log"
            file_handler = TimedRotatingFileHandler(
                log_file,
                when='midnight',  # Rotate at midnight
                interval=1,       # Every day
                backupCount=30,   # Keep 30 days of logs
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # Log the configuration
            root_logger.info(f"Logging configured with level: {logging.getLevelName(level)}")
            root_logger.info(f"Log file: {log_file}")
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False

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
    setup_logging(settings.logging.level, settings.logging.dir)

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