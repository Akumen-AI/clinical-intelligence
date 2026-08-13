# AI Clinical Intelligence Platform - Data Dictionary

This document outlines the database schema and definitions for the normalized Patient Identity and Clinical Entities.

## Patient Identity Layer

### `patients`
Core demographic table representing unique individuals.

| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | `VARCHAR(36)` | Primary Key. UUID for the patient. |
| `mrn` | `VARCHAR(100)` | Medical Record Number. Must be unique. |
| `name` | `VARCHAR(255)` | Full name of the patient. |
| `dob` | `VARCHAR(20)` | Date of Birth (ISO 8601 or clinical string format). |
| `sex` | `VARCHAR(20)` | Biological sex or gender. |
| `duplicate_of` | `VARCHAR(36)` | Foreign Key to `patients`. Used for fuzzy matching/merging (Story 4.4). |
| `created_at` | `DATETIME` | Timestamp of creation. |

### `visits`
Represents distinct healthcare encounters. Created automatically when a document is linked to a patient.

| Column | Type | Description |
|--------|------|-------------|
| `visit_id` | `VARCHAR(36)` | Primary Key. UUID for the visit. |
| `patient_id` | `VARCHAR(36)` | Foreign Key to `patients.patient_id`. |
| `document_id` | `VARCHAR(36)` | Foreign Key to `documents.document_id`. The document that sourced this visit. |
| `visit_date` | `VARCHAR(50)` | The date of the visit (extracted from document or upload timestamp). |
| `visit_type` | `VARCHAR(100)` | Type of visit (e.g., Inpatient, Outpatient, Lab). |
| `provider_name` | `VARCHAR(255)` | The name of the attending provider/physician. |
| `created_at` | `DATETIME` | Timestamp of creation. |

## Normalized Clinical Entities

These tables store structured clinical data extracted from documents, directly linked to a `patient_id`.

### `medications`
Prescribed or active medications.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key. Auto-incremented. |
| `patient_id` | `VARCHAR(36)` | Foreign Key to `patients.patient_id`. |
| `source_field_id` | `VARCHAR(36)` | Foreign Key to `extracted_fields.field_id`. Lineage tracking. |
| `raw_text` | `TEXT` | Raw extracted text for the medication. |
| `rxnorm_code` | `VARCHAR(50)` | Standardized RxNorm code. Intentionally left null pending Story 4.3. |
| `created_at` | `DATETIME` | Timestamp of creation. |

### `diagnoses`
Patient conditions and assessments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key. Auto-incremented. |
| `patient_id` | `VARCHAR(36)` | Foreign Key to `patients.patient_id`. |
| `source_field_id` | `VARCHAR(36)` | Foreign Key to `extracted_fields.field_id`. Lineage tracking. |
| `raw_text` | `TEXT` | Raw extracted condition description. |
| `icd10_code` | `VARCHAR(20)` | Extracted ICD-10 code (if available in raw text). |
| `snomed_code` | `VARCHAR(50)` | Standardized SNOMED CT code. Intentionally left null pending Story 4.3. |
| `created_at` | `DATETIME` | Timestamp of creation. |

### `lab_results`
Individual laboratory test results.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key. Auto-incremented. |
| `patient_id` | `VARCHAR(36)` | Foreign Key to `patients.patient_id`. |
| `source_field_id` | `VARCHAR(36)` | Foreign Key to `extracted_fields.field_id`. Lineage tracking. |
| `raw_text` | `TEXT` | Raw extracted lab result description. |
| `loinc_code` | `VARCHAR(50)` | Standardized LOINC code. Intentionally left null pending Story 4.3. |
| `created_at` | `DATETIME` | Timestamp of creation. |

### `vitals`
Patient vital signs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key. Auto-incremented. |
| `patient_id` | `VARCHAR(36)` | Foreign Key to `patients.patient_id`. |
| `source_field_id` | `VARCHAR(36)` | Foreign Key to `extracted_fields.field_id`. Lineage tracking. |
| `raw_text` | `TEXT` | Raw extracted text. |
| `type` | `VARCHAR(50)` | Type of vital (e.g., BP, Heart Rate). |
| `value` | `VARCHAR(100)` | Quantitative value. |
| `unit` | `VARCHAR(50)` | Unit of measurement. |
| `recorded_at` | `DATETIME` | Timestamp the vital was recorded (if available). |
| `created_at` | `DATETIME` | Timestamp of row creation. |

### `procedures`
Surgical and clinical procedures.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key. Auto-incremented. |
| `patient_id` | `VARCHAR(36)` | Foreign Key to `patients.patient_id`. |
| `source_field_id` | `VARCHAR(36)` | Foreign Key to `extracted_fields.field_id`. Lineage tracking. |
| `raw_text` | `TEXT` | Raw extracted procedure description. |
| `cpt_code` | `VARCHAR(20)` | Standardized CPT code. Intentionally left null pending Story 4.3. |
| `date` | `VARCHAR(50)` | Date of the procedure. |
| `created_at` | `DATETIME` | Timestamp of creation. |
