import re
with open("app/services/upload_service.py", "r") as f:
    content = f.read()
content = content.replace(
    'print(f"[Epic 2.2 Extraction Warning] Field extraction encountered an issue: {e}")',
    'import traceback; traceback.print_exc(); print(f"[Epic 2.2 Extraction Warning] Field extraction encountered an issue: {e}")'
)
with open("app/services/upload_service.py", "w") as f:
    f.write(content)
