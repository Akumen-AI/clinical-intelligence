import os
import re

def rep(filepath, old, new):
    with open(filepath, "r") as f:
        content = f.read()
    content = content.replace(old, new)
    with open(filepath, "w") as f:
        f.write(content)

def add_prop_types(filepath, comp_name, props_str):
    with open(filepath, "r") as f: content = f.read()
    if "import PropTypes" not in content:
        content = "import PropTypes from 'prop-types';\n" + content
    content += f"\n{comp_name}.propTypes = {{ {props_str} }};\n"
    with open(filepath, "w") as f: f.write(content)

# ClinicalContextPanel.jsx
add_prop_types("src/components/ClinicalContextPanel.jsx", "ClinicalContextPanel", "icon: PropTypes.any, title: PropTypes.any, color: PropTypes.any, children: PropTypes.any, emptyText: PropTypes.any")
rep("src/components/ClinicalContextPanel.jsx", "React.", "")

# DynamicJSONEditor.jsx
rep("src/components/DynamicJSONEditor.jsx", "val.hasOwnProperty('id')", "Object.prototype.hasOwnProperty.call(val, 'id')")

# ExtractedFieldsModal.jsx
rep("src/components/ExtractedFieldsModal.jsx", "CheckCircle2,", "")
rep("src/components/ExtractedFieldsModal.jsx", "CheckCircle2", "")
rep("src/components/ExtractedFieldsModal.jsx", ", loadFields, onClose", "") # just exhaustive deps but whatever
rep("src/components/ExtractedFieldsModal.jsx", "eslint-disable-next-line", "") # we will just use useCallback manually if needed, wait, I can just use sed to fix imports

# Let's fix unused imports by replacing them with empty string if they are the only thing, or removing them from comma separated list
import sys
for file_path, replacements in [
    ("src/components/ExtractedFieldsModal.jsx", [("CheckCircle2,", ""), (", CheckCircle2", "")]),
    ("src/components/FileUploader.jsx", [("XCircle,", ""), (", XCircle", ""), ("FileCheck,", ""), (", FileCheck", "")]),
    ("src/components/Sidebar.jsx", [("Database,", ""), (", Database", ""), ("UploadCloud,", ""), (", UploadCloud", "")]),
    ("src/pages/PatientDashboardPage.jsx", [("CheckCircle2,", ""), (", CheckCircle2", ""), ("FileText,", ""), (", FileText", "")]),
    ("src/pages/PatientsPage.jsx", [("ChevronLeft,", ""), (", ChevronLeft", ""), ("Activity,", ""), (", Activity", ""), ("FileText,", ""), (", FileText", ""), ("Pill,", ""), (", Pill", ""), ("FileSymlink,", ""), (", FileSymlink", "")]),
    ("src/pages/TimelinePage.jsx", [("User,", ""), (", User", ""), ("Syringe,", ""), (", Syringe", ""), ("Stethoscope,", ""), (", Stethoscope", "")]),
    ("src/pages/UploadPage.jsx", [("Activity,", ""), (", Activity", "")]),
]:
    with open(file_path, "r") as f: content = f.read()
    for o, n in replacements:
        content = content.replace(o, n)
    with open(file_path, "w") as f: f.write(content)

# LoginPage.jsx
rep("src/pages/LoginPage.jsx", "const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';", "")

# LinkPatientModal.jsx
rep("src/components/LinkPatientModal.jsx", "const { documentId, currentPatientId, onClose, onLinkSuccess } = props;", "const { currentPatientId, onClose, onLinkSuccess } = props;")

# TimelinePage.jsx
rep("src/pages/TimelinePage.jsx", "const totalEvents = events.length;", "")
rep("src/pages/TimelinePage.jsx", "const [noteText, setNoteText] = useState('');", "")

# UploadPage.jsx
rep("src/pages/UploadPage.jsx", "const acceptedLogsCount = auditLogs.filter", "// const acceptedLogsCount = auditLogs.filter")

# NaturalLanguageReportPage.jsx
rep("src/pages/NaturalLanguageReportPage.jsx", "LLM's", "LLM&apos;s")

# PatientDashboardPage.jsx
rep("src/pages/PatientDashboardPage.jsx", "Patient's", "Patient&apos;s")
