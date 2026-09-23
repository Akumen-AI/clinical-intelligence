import glob
import re
import os

files = glob.glob("app/**/*.py", recursive=True) + glob.glob("tests/**/*.py", recursive=True)

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    new_content = re.sub(r"except AccessDeniedError\b.*?:", "except HTTPException as e:", content)
    new_content = re.sub(r"raise AccessDeniedError\((.*?)\)", r"raise HTTPException(status_code=403, detail=\1)", new_content)
    # also if any tests are importing RbacAccessGuard, remove them
    if "RbacAccessGuard" in new_content and "test_" in filepath:
        new_content = re.sub(r"from app\.core\.patient_access_guard import RbacAccessGuard.*?\n", "", new_content)
        new_content = re.sub(
            r"RbacAccessGuard\(\)\.assert_can_query_patient\(([^,]+),\s*([^)]+)\)",
            r"AuthorizationService.verify_access(\1, ResourceType.PATIENT, Operation.READ, \2)",
            new_content
        )

    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
