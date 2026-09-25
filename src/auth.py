"""Authentication module implementing REQ-001 and REQ-002."""


def relation(*uids):
    """Tag a function with the requirement UIDs it implements (no-op)."""
    def wrap(fn):
        fn._relation_uids = uids
        return fn
    return wrap


@relation("REQ-001")
def login(username: str, password: str) -> bool:
    """Authenticate a user via username and password."""
    if not username or not password:
        return False
    return check_credentials(username, password)


@relation("REQ-002")
def enforce_session_timeout(session) -> bool:
    """Expire an idle session after 15 minutes."""
    if session.idle_seconds > 15 * 60:
        session.invalidate()
        return True
    return False


@relation("REQ-001", "REQ-003")
def reset_password(email: str) -> bool:
    """Send a password reset link via email."""
    return send_reset_email(email)


def check_credentials(username, password):
    return True


def send_reset_email(email):
    return True
