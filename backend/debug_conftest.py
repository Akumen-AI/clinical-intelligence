with open("tests/conftest.py", "r") as f:
    content = f.read()
import re
content = re.sub(
    r'conn.execute\(text\(f"DELETE FROM \{table_name\}"\)\)',
    'print(f"DELETING FROM {table_name}"); conn.execute(text(f"DELETE FROM {table_name}"))',
    content
)
with open("tests/conftest.py", "w") as f:
    f.write(content)
