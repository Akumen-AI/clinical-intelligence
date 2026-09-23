import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    if 'print(' not in content and 'except Exception' not in content:
        return

    # Add structlog import if needed
    if 'import structlog' not in content and 'print(' in content:
        content = 'import structlog\nlogger = structlog.get_logger(__name__)\n\n' + content

    # Replace print(f"...") with logger.info(...)
    # Using a simple regex to replace print( with logger.info(
    content = re.sub(r'print\((.*?)\)', r'logger.info(\1)', content)

    with open(filepath, 'w') as f:
        f.write(content)

for root, _, files in os.walk('app/services'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
