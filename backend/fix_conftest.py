with open("tests/conftest.py", "r") as f:
    content = f.read()

import re

clear_db_code = """
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
        for table_name in Base.metadata.tables.keys():
            conn.execute(text(f"DELETE FROM {table_name}"))
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        conn.commit()
"""

# Let's insert the clear_db_code BEFORE yield
replacement = clear_db_code + "\n    yield"
content = content.replace("yield", replacement, 1)

with open("tests/conftest.py", "w") as f:
    f.write(content)
