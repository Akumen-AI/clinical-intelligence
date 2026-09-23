with open("tests/api/test_audit_log.py", "r") as f:
    content = f.read()

content = content.replace("client = TestClient(app)", "")
content = content.replace(
    "def get_compliance_token():\n    return create_access_token(data={\"sub\": str(uuid.uuid4()), \"role\": \"compliance\", \"email\": \"compliance@clinic.org\"})", 
    ""
)
content = content.replace(
    "def get_doctor_token():\n    return create_access_token(data={\"sub\": str(uuid.uuid4()), \"role\": \"doctor\", \"email\": \"doctor@clinic.org\"})",
    ""
)

# Patch test signatures
content = content.replace("def test_audit_log_append_only():", "def test_audit_log_append_only(client_as):")
content = content.replace("def test_get_audit_logs_compliance_role():", "def test_get_audit_logs_compliance_role(client_as):")
content = content.replace("def test_get_audit_logs_doctor_role_forbidden():", "def test_get_audit_logs_doctor_role_forbidden(client_as):")
content = content.replace("def test_get_patient_audit_logs():", "def test_get_patient_audit_logs(client_as):")

# Patch client creation
content = content.replace("token = get_compliance_token()\n    headers = {\"Authorization\": f\"Bearer {token}\"}\n    \n    # Try to PATCH\n    patch_response = client.patch", "client = client_as('compliance')\n    patch_response = client.patch")
content = content.replace("token = get_compliance_token()\n    headers = {\"Authorization\": f\"Bearer {token}\"}\n    response = client.get", "client = client_as('compliance')\n    response = client.get")
content = content.replace("token = get_doctor_token()\n    headers = {\"Authorization\": f\"Bearer {token}\"}\n    response = client.get", "client = client_as('doctor')\n    response = client.get")
content = content.replace("token = get_compliance_token()\n    headers = {\"Authorization\": f\"Bearer {token}\"}", "client = client_as('compliance')\n    headers = {}")

with open("tests/api/test_audit_log.py", "w") as f:
    f.write(content)
