"""
Reference only: shows the @relation marker form StrictDoc 0.30.4 reads.
Copy the docstring lines into your own src/auth.py functions.
"""


def login(username: str, password: str) -> bool:
    """
    Username/password login (kept for audit; requirement is Obsolete).

    @relation(REQ-001, scope=function)
    """
    raise NotImplementedError


def enforce_session_timeout(session, now) -> bool:
    """
    Expire the session after 15 minutes of inactivity.

    @relation(REQ-002, scope=function)
    """
    return (now - session.last_seen).total_seconds() > 15 * 60


def login_via_sso(assertion) -> bool:
    """
    Authenticate a user from the SSO provider's signed assertion.

    @relation(REQ-004, scope=function)
    """
    return assertion.is_valid()
