import os
import sys

# Add backend directory to python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.tests.test_confidence_router import *  # noqa: F401, F403
