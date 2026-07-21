import getpass
import logging
import sys

from garminconnect import Garmin

from training_sync.config import garmin_token_path

logger = logging.getLogger(__name__)


def get_client() -> Garmin:
    """Return an authenticated Garmin client using the Training Sync token store."""
    token_file = garmin_token_path()

    client = Garmin()
    needs_login = True

    if token_file.exists():
        try:
            client.login(tokenstore=str(token_file))
            needs_login = False
            logger.info("Logged in using stored token.")
        except Exception:
            logger.warning("Stored token expired or invalid.")

    if needs_login:
        if not sys.stdin.isatty():
            sys.exit("Error: Garmin session expired. Please run interactively to log in.")
        email = input("Garmin Email: ")
        password = getpass.getpass("Garmin Password: ")
        client = Garmin(email, password)
        try:
            token_file.parent.mkdir(parents=True, exist_ok=True)
            client.login(tokenstore=str(token_file))
            token_file.chmod(0o600)
            logger.info("Interactive login successful.")
        except Exception as exc:
            raise RuntimeError(f"Login failed: {exc}") from exc

    return client
