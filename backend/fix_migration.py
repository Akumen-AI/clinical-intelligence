with open("alembic/versions/c70d8c54004c_add_refresh_tokens_table.py", "r") as f:
    content = f.read()

content = content.replace("    try:\n", "")
content = content.replace("    except Exception:\n        pass\n", "")

with open("alembic/versions/c70d8c54004c_add_refresh_tokens_table.py", "w") as f:
    f.write(content)
