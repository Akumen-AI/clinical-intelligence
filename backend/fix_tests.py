import os
import glob

test_files = glob.glob('tests/**/*.py', recursive=True)

for file in test_files:
    if file == 'tests/conftest.py':
        continue
        
    with open(file, 'r') as f:
        content = f.read()
        
    # Many tests define their own get_token or use create_access_token manually
    # The most common pattern is `create_access_token({"sub": ...})`
    # Instead of fixing each one, we can just patch `get_current_user` in the test files
    pass
