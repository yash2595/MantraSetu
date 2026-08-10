def pytest_ignore_collect(path, config):
    """Ignore the auth_verification_test.py script during collection."""
    if path.basename == "auth_verification_test.py":
        return True
    return False
