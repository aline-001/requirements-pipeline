"""Authentication module implementing REQ-001 and REQ-002."""


def relation(*uids):
    """Tag a function with the requirement UIDs it implements (no-op)."""
    def wrap(fn):
        fn._relation_uids = uids
        return fn
    return wrap


def login(username: str, password: str) -> bool:
    """Authenticate a user via username and password.

    @relation(REQ-001, scope=function)
    """
    if not username or not password:
        return False
    return check_credentials(username, password)


def enforce_session_timeout(session) -> bool:
    """Expire an idle session after 15 minutes.

    @relation(REQ-002, scope=function)
    """
    if session.idle_seconds > 15 * 60:
        session.invalidate()
        return True
    return False


def reset_password(email: str) -> bool:
    """Send a password reset link via email.

    Implements REQ-003, which is still Draft. Add the StrictDoc relation tag for REQ-003 once it is approved and synced.
    """
    return send_reset_email(email)


def check_credentials(username, password):
    return True


def send_reset_email(email):
    return True


def login_via_sso(provider_token: str) -> bool:
    """Authenticate a user via an SSO provider token.

    @relation(REQ-004, scope=function)
    """
    return validate_sso_token(provider_token)


def validate_sso_token(provider_token):
    return bool(provider_token)
