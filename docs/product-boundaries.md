# Product Boundaries

## Administrative Assistant Only
This application is strictly an **administrative assistant** to help organize clinical documents, extract billing and operational metrics, and search policies. 
**It is not a medical device.** It does not provide diagnoses or treatment recommendations.

## Human in the Loop (HitL)
The platform features an automated confidence evaluation stage. Any extracted entity falling below the predefined confidence threshold (`0.80` by default), or any field explicitly flagged as illegible or requiring review, is sent to a mandatory Review Queue. 
No uncertain data enters the Canonical Patient Record without explicit sign-off from an authorized clinical user (Doctor or Nurse).

## Synthetic Demo Data
To protect Patient Health Information (PHI), the repository includes zero real clinical data. A seed script (`seed_all_demo_data.py`) algorithmically generates believable, completely synthetic records to demonstrate platform capabilities.
