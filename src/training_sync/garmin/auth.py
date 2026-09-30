import getpass
import logging
import sys

from garminconnect import Garmin
from requests.exceptions import RequestException

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
        except Exception as exc:
            if _caused_by_network_failure(exc):
                sys.exit(
                    "Error: Could not validate the stored Garmin session because a "
                    "network connection failed. Retry when Garmin is reachable; "
                    "re-login is needed only if Garmin rejects the session."
                )
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


def _caused_by_network_failure(exc: BaseException) -> bool:
    """Distinguish transport errors from rejected credentials without exposing details."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (RequestException, ConnectionError, TimeoutError)):
            return True
        current = current.__cause__ or current.__context__
    return False
