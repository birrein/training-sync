import os
import sys
import getpass
import logging
from garminconnect import Garmin

logger = logging.getLogger(__name__)

def get_client() -> Garmin:
    """
    Retrieves an authenticated Garmin client.
    Checks the current directory or the package directory for a saved session token.
    Falls back to interactive CLI login if no valid token is found.
    """
    # Try looking in current working directory first, fallback to package dir
    token_file = "garmin_token.json"
    if not os.path.exists(token_file):
        token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garmin_token.json")
        
    client = Garmin()
    needs_login = True
    
    if os.path.exists(token_file):
        try:
            client.login(tokenstore=token_file)
            needs_login = False
            logger.info("Logged in using stored token.")
        except Exception:
            logger.warning("Stored token expired or invalid.")
            needs_login = True
            
    if needs_login:
        if not sys.stdin.isatty():
            sys.exit("Error: Garmin session expired. Please run interactively to log in.")
        email = input("Garmin Email: ")
        password = getpass.getpass("Garmin Password: ")
        client = Garmin(email, password)
        try:
            client.login(tokenstore=token_file)
            logger.info("Interactive login successful.")
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")
            
    return client
