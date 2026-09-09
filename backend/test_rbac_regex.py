import re

RBAC_MATRIX = {
    "/api/v1/patients": {"NURSE"},
    "/api/v1/patients/{id}/ask": {"DOCTOR"}
}

def get_roles(path):
    best_match = ""
    allowed_roles = set()
    for prefix, config in RBAC_MATRIX.items():
        pattern = "^" + re.sub(r'\{[^}]+\}', '[^/]+', prefix)
        if re.match(pattern, path) and len(prefix) > len(best_match):
            best_match = prefix
            allowed_roles = config
    return best_match, allowed_roles

print(get_roles("/api/v1/patients/123"))
print(get_roles("/api/v1/patients/123/ask"))
print(get_roles("/api/v1/patients/123/context-panel"))
