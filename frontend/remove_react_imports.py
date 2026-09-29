import json
import re
import os

with open("lint-results.json", "r") as f:
    results = json.load(f)

for file_result in results:
    if file_result["errorCount"] == 0 and file_result["warningCount"] == 0:
        continue
        
    file_path = file_result["filePath"]
    with open(file_path, "r") as f:
        content = f.read()

    # 1. Fix "React" unused
    # Replace `import React, {` with `import {`
    content = re.sub(r"import React,\s*\{", "import {", content)
    # Replace `import React from 'react';\n` with nothing
    content = re.sub(r"import React from ['\"]react['\"];?\n", "", content)
    
    # 2. Fix unescaped entities
    # It's tricky to do universally without an AST, but we can fix specific lines if needed, or just let eslint ignore it? NO, no ignores.
    # Let's fix specific files manually using replace_file_content or a custom script block later.
    
    # 3. Write back
    with open(file_path, "w") as f:
        f.write(content)
