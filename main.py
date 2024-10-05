import asyncio
import logging

# Configuration placeholder
CONFIG = {
    'example_key': 'example_value'
}

# Set up basic logging
logging.basicConfig(level=logging.INFO)

async def example_async_function():
    """An example asynchronous function."""
    try:
        logging.info("Starting async operation")
        await asyncio.sleep(1)  # Simulate an async I/O operation
        logging.info("Async operation completed")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

def main():
    """Main function to run the application."""
    logging.info("Application started")
    asyncio.run(example_async_function())
    logging.info("Application finished")

if __name__ == "__main__":
    main()
