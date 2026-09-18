"""Minimal login credential check backing REQ-001 and TASK-001.

This tiny module exists so `specripple verify` can pin documented behavior
to executable code via the `command` checker.
"""

VALID_USERS = {
    "alice@example.com": "wonderland",
}


def check_credentials(email: str, password: str) -> bool:
    """Return True when the credentials are valid."""
    return VALID_USERS.get(email) == password


def login(email: str, password: str) -> str:
    """Return the observable login outcome for the given credentials."""
    if check_credentials(email, password):
        return "session issued"
    return "login failed"
