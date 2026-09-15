# Vocabulary Normalization (FR-15)

## Implementation Scope

The clinical vocabulary normalization feature (FR-15) for ICD-10, SNOMED CT, RxNorm, and LOINC is currently implemented as an **"inline extraction"** mechanism rather than a live lookup against an authoritative terminology service.

This means the system will capture and normalize these codes *only if they are explicitly stated in the source document* alongside the clinical entity (e.g., `Essential Hypertension [SNOMED 59621000]`). The system uses regex pattern matching and targeted LLM extraction to identify these labeled codes from the raw text.

## Rationale & Licensing Considerations

This scoped implementation represents a deliberate design choice based on the following considerations:

1. **Licensing Constraints**: While RxNorm and LOINC are free and publicly available (maintained by the US National Library of Medicine), SNOMED CT is a licensed terminology in most jurisdictions. 
2. **Regulatory Uncertainty**: As noted in Section 11.1 of the BRD, the applicable regulatory jurisdiction for this deployment has not yet been confirmed. Therefore, no SNOMED terminology license is assumed or required by the current implementation. A live terminology server would mandate a valid license and registration in many regions.

## Future State: Live Terminology Integration

A future, fully-fledged integration (out of scope for the current build) would involve:

- **Live Terminology Servers**: Calling a hosted terminology server (e.g., a FHIR terminology service or specialized API for SNOMED CT, RxNorm, and LOINC).
- **Free-Text Resolution**: Resolving free-text conditions, medications, and labs that were *not* explicitly coded in the source document by passing the raw text to the terminology service to retrieve the canonical code and standard concept name.
- **Auto-Coding**: Enhancing the canonical records with these resolved codes, vastly improving interoperability and analytics without requiring the original physician to manually document the code.
