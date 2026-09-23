import os
import re

TESTS_DIR = "tests"

# Files to exclude from automated patching
EXCLUDE_FILES = ["test_auth_hardening.py", "test_audit_coverage_enforced.py", "conftest.py"]

# We will look for: create_access_token(data={"sub": str(uuid.uuid4()), "role": "compliance", ...})
# and we need to make sure the user is in the database.
# Actually, the easiest way is to add an autouse fixture in conftest.py that patches app.core.security.get_current_user
# Wait, if we patch get_current_user in conftest, test_auth_hardening will fail?
# No! test_auth_hardening can just unpatch it for its specific tests!

# Let's do the get_current_user patch in conftest.py:
