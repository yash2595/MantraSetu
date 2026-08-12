def pytest_ignore_collect(collection_path=None, path=None, config=None):
    """Ignore the auth_verification_test.py script during collection."""
    p = collection_path or path
    if p and getattr(p, "name", getattr(p, "basename", "")) == "auth_verification_test.py":
        return True
    return False

