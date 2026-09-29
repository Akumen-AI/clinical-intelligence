import json
import re
import os
from collections import defaultdict

with open("lint-results.json", "r") as f:
    results = json.load(f)

for file_result in results:
    file_path = file_result["filePath"]
    prop_types_to_add = defaultdict(set)
    unused_vars = []
    
    for msg in file_result["messages"]:
        if msg["ruleId"] == "react/prop-types":
            m = re.search(r"'([^']+)' is missing in props validation", msg["message"])
            if m:
                prop = m.group(1).split('.')[0].replace('[]', '')
                prop_types_to_add[prop].add(prop)
        elif msg["ruleId"] == "no-unused-vars":
            m = re.search(r"'([^']+)' is defined but never used", msg["message"])
            if m:
                unused_vars.append(m.group(1))
    
    if prop_types_to_add or unused_vars:
        with open(file_path, "r") as f:
            content = f.read()
        
        # Inject PropTypes import if not exists and we need it
        if prop_types_to_add and "import PropTypes" not in content:
            content = "import PropTypes from 'prop-types';\n" + content
            
        basename = os.path.basename(file_path).split('.')[0]
        
        if prop_types_to_add:
            props_str = ",\n  ".join([f"{p}: PropTypes.any" for p in prop_types_to_add.keys()])
            injection = f"\n{basename}.propTypes = {{\n  {props_str}\n}};\n"
            
            if f"{basename}.propTypes" not in content:
                content += injection
                
        with open(file_path, "w") as f:
            f.write(content)
