# Data Model

The platform uses a relational SQLite database via SQLAlchemy.

## Core Entities

- **User**: System users mapped to RBAC roles.
- **Patient**: Core patient demographic record.
- **Document**: Represents an uploaded file and its current processing state.
- **ExtractedField**: Raw clinical entity extracted from a document by the LLM.
- **PendingReview**: Extracted fields that fall below the system confidence threshold, awaiting human verification.
- **CanonicalPatientRecord**: Verified, unified clinical data for a patient.
- **AuditLog**: Append-only log of security-sensitive events.
- **CorrectionLog**: Records explicit human overrides made in the Review Queue.
- **UploadLog**: Audit trail of successful and rejected document upload attempts.

## Entity Categories
Structured extraction currently covers:
1. Patient Demographics
2. Vital Signs
3. Diagnoses
4. Medications
5. Lab Results
6. Clinical Dates
7. Ordering/Attending Physician
