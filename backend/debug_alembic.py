with open("alembic/env.py", "r") as f:
    content = f.read()

import re
content = content.replace("context.run_migrations()", "print('RUNNING MIGRATIONS!!!'); context.run_migrations()")
with open("alembic/env.py", "w") as f:
    f.write(content)
