# agentic_platform/agentic_platform/utils/json_utils.py

import json
import logging
import re

logger = logging.getLogger(__name__)

def extract_json_from_output(messages):
    """
    Extracts JSON object from a list of strings.

    Args:
        messages (list): A list of strings containing the output messages.

    Returns:
        dict or None: Parsed JSON object if found, else None.
    """
    for message in messages:
        try:
            # Use regex to find JSON-like structure
            json_match = re.search(r'\{.*\}', message, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string: {json_str}")
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            logger.debug(f"Problematic message: {message}")
    logger.warning("No valid JSON found in the output")
    return None  # Return None if no valid JSON is found
