from clipboard import Clipboard
from replacer import Replacer

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    replacer = Replacer()
    clipboard = Clipboard(
        callbacks={
            "text": Clipboard.callback_edit(replacer.apply_rules),
            "unicode": Clipboard.callback_edit(replacer.apply_rules),
        },
        default_callback=Clipboard.callback_nop(),
    )

    logger.info("Clipboard replacement service started (Press Ctrl+C to exit).")
    try:
        clipboard.listen()
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise e
    finally:
        logger.info("Exiting...")

if __name__ == "__main__":
    main()
