import re
from typing import Optional, Dict, Any, List
from app.services.extraction.base import ClinicalFieldExtractor, ExtractionResult
from app.schemas.extracted_field import (
    ClinicalFieldsSchema,
    PatientIdentifierSchema,
    PhysicianSchema,
    VitalsSchema,
    DiagnosisItemSchema,
    MedicationItemSchema,
    LabResultItemSchema,
)


class RuleBasedFieldExtractor(ClinicalFieldExtractor):
    """
    Deterministic rule and regex-based clinical field extractor.
    Extracts key fields from standard clinical texts and patterns.
    Ensures missing fields are explicitly represented as null.
    """

    def extract(self, text: str, document_type: Optional[str] = None) -> ExtractionResult:
        if not text or not text.strip():
            return ExtractionResult(fields=ClinicalFieldsSchema(), confidence=0.0)

        patient = self._extract_patient(text)
        doc_date = self._extract_date(text)
        physician = self._extract_physician(text)
        vitals = self._extract_vitals(text)
        diagnosis = self._extract_diagnosis(text)
        medications = self._extract_medications(text)
        lab_results = self._extract_lab_results(text)
        symptoms = self._extract_symptoms(text)
        procedures = self._extract_procedures(text)

        fields = ClinicalFieldsSchema(
            patient_identifier=patient,
            document_date=doc_date,
            ordering_physician=physician,
            vitals=vitals,
            diagnosis=diagnosis,
            medications=medications,
            lab_results=lab_results,
            symptoms=symptoms,
            procedures=procedures,
        )

        found_fields = sum([
            patient is not None,
            doc_date is not None,
            physician is not None,
            vitals is not None,
            diagnosis is not None,
            medications is not None,
            lab_results is not None,
            symptoms is not None,
            procedures is not None,
        ])
        confidence = min(1.0, max(0.5, found_fields / 5.0)) if found_fields > 0 else 0.0

        return ExtractionResult(
            fields=fields,
            confidence=round(confidence, 2),
            field_confidences={
                "patient_identifier": 0.90 if patient else 0.0,
                "document_date": 0.95 if doc_date else 0.0,
                "ordering_physician": 0.90 if physician else 0.0,
                "vitals": 0.88 if vitals else 0.0,
                "diagnosis": 0.85 if diagnosis else 0.0,
                "medications": 0.90 if medications else 0.0,
                "lab_results": 0.92 if lab_results else 0.0,
                "symptoms": 0.80 if symptoms else 0.0,
                "procedures": 0.80 if procedures else 0.0,
            },
        )

    def _extract_patient(self, text: str) -> Optional[PatientIdentifierSchema]:
        name = None
        patient_id = None
        dob = None
        gender = None

        name_match = re.search(
            r"(?:Patient(?:\s+Name)?|Name|Pt Name)\s*:\s*([A-Za-z\s,\.\'-]+?)(?:\n|\r|DOB|Age|Gender|Sex|MRN|ID|Date|$)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            candidate = name_match.group(1).strip()
            if candidate and len(candidate) > 2:
                name = candidate

        id_match = re.search(
            r"(?:Patient\s*ID|MRN|Record\s*#|UHID|Reg(?:\s*No)?)\s*:\s*([A-Za-z0-9\-_]+)",
            text,
            re.IGNORECASE,
        )
        if id_match:
            patient_id = id_match.group(1).strip()

        dob_match = re.search(
            r"(?:DOB|Date\s*of\s*Birth|Birth\s*Date)\s*:\s*([0-9]{1,4}[/\-\.][0-9]{1,2}[/\-\.][0-9]{1,4})",
            text,
            re.IGNORECASE,
        )
        if dob_match:
            dob = dob_match.group(1).strip()

        gender_match = re.search(
            r"(?:Gender|Sex)\s*:\s*(Male|Female|M|F|Other)",
            text,
            re.IGNORECASE,
        )
        if gender_match:
            val = gender_match.group(1).strip().capitalize()
            if val == "M":
                val = "Male"
            elif val == "F":
                val = "Female"
            gender = val

        if any([name, patient_id, dob, gender]):
            return PatientIdentifierSchema(
                patient_id=patient_id,
                name=name,
                dob=dob,
                gender=gender,
            )
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        date_match = re.search(
            r"(?:Date|Encounter\s*Date|Visit\s*Date|Report\s*Date|Prescription\s*Date|Collection\s*Date)\s*:\s*([0-9]{1,4}[/\-\.][0-9]{1,2}[/\-\.][0-9]{1,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+[0-9]{1,2},?\s+[0-9]{4}\b)",
            text,
            re.IGNORECASE,
        )
        if date_match:
            return date_match.group(1).strip()

        fallback = re.search(
            r"\b(20[2-3][0-9][\-/][0-1][0-9][\-/][0-3][0-9])\b",
            text,
        )
        if fallback:
            return fallback.group(1).strip()
        return None

    def _extract_physician(self, text: str) -> Optional[PhysicianSchema]:
        doc_match = re.search(
            r"(?:Dr\.\s+[A-Za-z\s\.\'-]+|(?:Doctor|Physician|Ordering\s*(?:Doctor|Physician|Provider)|Prescribing\s*Doctor|Consultant)\s*:\s*([A-Za-z\s\.\'-]+?)(?:\n|\r|Department|NPI|License|Signature|$))",
            text,
            re.IGNORECASE,
        )
        if doc_match:
            matched = doc_match.group(0).strip()
            if ":" in matched:
                name = matched.split(":", 1)[1].strip()
            else:
                name = matched
            name = name.split("\n")[0].strip()

            dept_match = re.search(r"Department\s*:\s*([^\n\r]+)", text, re.IGNORECASE)
            dept = dept_match.group(1).strip() if dept_match else None

            if name:
                return PhysicianSchema(name=name, department=dept)
        return None

    def _extract_vitals(self, text: str) -> Optional[VitalsSchema]:
        bp = None
        hr = None
        rr = None
        temp = None
        spo2 = None
        weight = None
        height = None
        bmi = None

        bp_match = re.search(r"(?:BP|Blood\s*Pressure)\s*:\s*([0-9]{2,3}/[0-9]{2,3}(?:\s*mmHg)?)", text, re.IGNORECASE)
        if bp_match:
            bp = bp_match.group(1).strip()

        hr_match = re.search(r"(?:HR|Heart\s*Rate|Pulse(?:\s*Rate)?)\s*:\s*([0-9]{2,3}(?:\s*(?:bpm|/min))?)", text, re.IGNORECASE)
        if hr_match:
            hr = hr_match.group(1).strip()

        temp_match = re.search(r"(?:Temp(?:erature)?)\s*:\s*([0-9]{2,3}(?:\.[0-9])?\s*(?:°?F|°?C|F|C))", text, re.IGNORECASE)
        if temp_match:
            temp = temp_match.group(1).strip()

        rr_match = re.search(r"(?:RR|Respiratory\s*Rate)\s*:\s*([0-9]{1,2}(?:\s*(?:/min|bpm))?)", text, re.IGNORECASE)
        if rr_match:
            rr = rr_match.group(1).strip()

        spo2_match = re.search(r"(?:SpO2|Oxygen\s*Saturation|O2\s*Sat)\s*:\s*([0-9]{2,3}\s*%)", text, re.IGNORECASE)
        if spo2_match:
            spo2 = spo2_match.group(1).strip()

        weight_match = re.search(r"(?:Weight|Wt)\s*:\s*([0-9]{1,3}(?:\.[0-9])?\s*(?:kg|lbs|pounds)?)", text, re.IGNORECASE)
        if weight_match:
            weight = weight_match.group(1).strip()

        height_match = re.search(r"(?:Height|Ht)\s*:\s*([0-9]{2,3}(?:\.[0-9])?\s*(?:cm|in|feet)?|[0-9]'[0-9]{1,2}\"?)", text, re.IGNORECASE)
        if height_match:
            height = height_match.group(1).strip()

        bmi_match = re.search(r"(?:BMI)\s*:\s*([0-9]{1,2}(?:\.[0-9])?)", text, re.IGNORECASE)
        if bmi_match:
            bmi = bmi_match.group(1).strip()

        if any([bp, hr, temp, rr, spo2, weight, height, bmi]):
            return VitalsSchema(
                blood_pressure=bp,
                heart_rate=hr,
                respiratory_rate=rr,
                temperature=temp,
                spo2=spo2,
                weight=weight,
                height=height,
                bmi=bmi,
            )
        return None

    def _extract_diagnosis(self, text: str) -> Optional[List[DiagnosisItemSchema]]:
        diag_section = re.search(
            r"(?:Diagnosis|Diagnoses|Assessment|Impression|Primary\s*Diagnosis)\s*:\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*(?:Medications|Discharge|Rx|Plan|Vitals|Orders|Procedures?|Signature|Doctor|Physician|$))",
            text,
            re.IGNORECASE,
        )
        if diag_section:
            raw_text = diag_section.group(1).strip()
            items = []
            for line in raw_text.split("\n"):
                line = re.sub(r"^[\-\*\d\.\s]+", "", line).strip()
                if line and len(line) > 2:
                    icd_match = re.search(r"[\(\[]([A-TV-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?)[\)\]]", line)
                    icd_code = icd_match.group(1) if icd_match else None
                    condition_name = re.sub(r"[\(\[][A-TV-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?[\)\]]", "", line).strip()
                    items.append(DiagnosisItemSchema(
                        condition_name=condition_name or line,
                        icd10_code=icd_code,
                    ))
            if items:
                return items
        return None

    def _extract_medications(self, text: str) -> Optional[List[MedicationItemSchema]]:
        med_section = re.search(
            r"(?:Medications|Rx|Prescription|Current\s*Medications|Discharge\s*Medications)\s*:\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*(?:Instructions|Advice|Follow\s*up|Procedures?|Signature|Doctor|Physician|Lab|Tests|$))",
            text,
            re.IGNORECASE,
        )
        if med_section:
            raw_text = med_section.group(1).strip()
            meds = []
            for line in raw_text.split("\n"):
                line = re.sub(r"^[\-\*\d\.\s]+", "", line).strip()
                if line and len(line) > 2:
                    dosage_match = re.search(r"(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|IU|units|tablets?|capsules?))", line, re.IGNORECASE)
                    dosage = dosage_match.group(1) if dosage_match else None

                    freq_match = re.search(r"\b(once\s+daily|twice\s+daily|thrice\s+daily|daily|BID|TID|QID|PRN|Q8H|Q12H|Q4H|at\s+bedtime|stat)\b", line, re.IGNORECASE)
                    frequency = freq_match.group(1) if freq_match else None

                    route_match = re.search(r"\b(oral|PO|IV|topical|subcutaneous|SC|IM|inhalation)\b", line, re.IGNORECASE)
                    route = route_match.group(1) if route_match else None

                    duration_match = re.search(r"(?:for|x)\s*(\d+\s*(?:days?|weeks?|months?))", line, re.IGNORECASE)
                    duration = duration_match.group(1) if duration_match else None

                    med_name = line
                    if dosage:
                        med_name = med_name.split(dosage)[0].strip()
                    elif freq_match:
                        med_name = med_name.split(freq_match.group(0))[0].strip()

                    meds.append(MedicationItemSchema(
                        medication_name=med_name or line,
                        dosage=dosage,
                        frequency=frequency,
                        route=route,
                        duration=duration,
                        instructions=line if not dosage else None,
                    ))
            if meds:
                return meds
        return None

    def _extract_lab_results(self, text: str) -> Optional[List[LabResultItemSchema]]:
        lab_results = []
        pattern = re.compile(
            r"([A-Za-z0-9\s\-_/]+)\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%^0-9\-_]+)?(?:\s*\(([^)]+)\))?(?:\s*(Normal|High|Low|Abnormal|H|L))?",
            re.IGNORECASE,
        )

        # Fields that look like lab results but aren't — expanded to catch
        # phone numbers, timestamps, barcodes, and document metadata
        vitals_and_meta = {
            "date", "dob", "bp", "hr", "pulse", "temp", "rr", "spo2", "weight", "height", "bmi",
            "age", "page", "phone", "fax", "patient", "mrn", "id",
            "ph", "lab", "no", "collection", "report", "sample", "location", "barcode",
            "reg", "email", "website", "www", "address", "pin", "zip", "code",
        }

        # Patterns that indicate the "value" is actually a phone number or time
        phone_pattern = re.compile(r"^\d{3,4}$")  # e.g., "0484" from "Ph: 0484-4012345"
        time_unit_pattern = re.compile(r"^(AM|PM|am|pm)$")

        for line in text.split("\n"):
            line = line.strip()
            match = pattern.match(line)
            if match:
                test_name = match.group(1).strip()
                # Check if any metadata keyword appears in test name
                test_name_lower = test_name.lower().strip()
                if any(v == test_name_lower or v in test_name_lower.split() for v in vitals_and_meta):
                    continue
                val = match.group(2).strip() if match.group(2) else None
                unit = match.group(3).strip() if match.group(3) else None
                ref_range = match.group(4).strip() if match.group(4) else None
                flag = match.group(5).strip() if match.group(5) else None

                # Skip entries where the unit looks like a phone suffix or time
                if unit and (re.match(r"^-\d{5,}$", unit) or time_unit_pattern.match(unit)):
                    continue
                # Skip if value looks like part of a phone number (3-4 digits followed
                # by a dash-prefixed unit) — e.g., Ph: 0484-4012345
                if val and unit and phone_pattern.match(val) and unit.startswith("-"):
                    continue

                if flag:
                    if flag.upper() == "H":
                        flag = "High"
                    elif flag.upper() == "L":
                        flag = "Low"
                    else:
                        flag = flag.capitalize()

                if test_name and val:
                    lab_results.append(LabResultItemSchema(
                        test_name=test_name,
                        value=val,
                        unit=unit,
                        reference_range=ref_range,
                        flag=flag,
                    ))

        if lab_results:
            return lab_results
        return None

    def _extract_symptoms(self, text: str) -> Optional[List[str]]:
        sym_match = re.search(
            r"(?:Chief\s*Complaint|Symptoms|Presenting\s*Complaint)\s*:\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*(?:Diagnosis|Assessment|Medications|Vitals|Orders|Procedures?|$))",
            text,
            re.IGNORECASE,
        )
        if sym_match:
            raw = sym_match.group(1).strip()
            items = [re.sub(r"^[\-\*\d\.\s]+", "", line).strip() for line in raw.split("\n") if line.strip()]
            if items:
                return items
        return None

    def _extract_procedures(self, text: str) -> Optional[List[str]]:
        proc_match = re.search(
            r"(?:Procedures?|Interventions?|Surgeries)\s*:\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\s*(?:Diagnosis|Assessment|Medications|Discharge|Rx|Plan|Vitals|Orders|Signature|$))",
            text,
            re.IGNORECASE,
        )
        if proc_match:
            raw = proc_match.group(1).strip()
            items = [re.sub(r"^[\-\*\d\.\s]+", "", line).strip() for line in raw.split("\n") if line.strip()]
            if items:
                return items
        return None
