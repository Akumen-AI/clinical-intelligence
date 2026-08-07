#!/usr/bin/env python3
"""
Synthetic handwriting test set generator for handwriting extraction evaluation.

Generates prescription-style images rendered with cursive Google Fonts to
simulate handwritten clinical documents. Each sample is a PNG image paired
with a JSON ground-truth file containing the exact field values used to render.

Samples are generated across three legibility tiers:
  - Clean (8 samples):    clear handwriting font, no degradation
  - Moderate (6 samples): slight blur, rotation ±3°, mild noise
  - Degraded (6 samples): heavy blur, rotation ±8°, low contrast, speckle noise

Output directory: scripts/handwriting_testset/

Usage:
    python scripts/generate_handwriting_testset.py

NOTE: Synthetic cursive-font renders are a reasonable proxy for messy handwriting
but are meaningfully cleaner and more consistent than real doctor handwriting.
Treat the 90% KPI on synthetic data as a pre-launch gate, not a substitute for
validating against real (de-identified or dummy) handwritten samples.
"""

import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "handwriting_testset")

FONT_FILES = [
    # Bundled Google Font (successfully downloaded)
    os.path.join(FONTS_DIR, "Caveat.ttf"),
    # macOS system handwriting/cursive fonts (excellent for simulating
    # real handwritten prescriptions — more realistic than Google Fonts)
    "/System/Library/Fonts/Noteworthy.ttc",
    "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
    "/System/Library/Fonts/MarkerFelt.ttc",
]

# ---------------------------------------------------------------------------
# Sample data pools — realistic clinical values for generating prescriptions
# ---------------------------------------------------------------------------

PATIENT_NAMES = [
    "Sarah Johnson", "Michael Chen", "Priya Patel", "James Williams",
    "Maria Garcia", "Robert Kim", "Emily Brown", "David Martinez",
    "Aisha Mohammed", "Thomas Anderson", "Li Wei", "Rachel Thompson",
    "Carlos Rivera", "Jennifer Lee", "Ahmed Hassan", "Susan Clark",
    "Raj Sharma", "Olivia Wilson", "Daniel Nguyen", "Laura Taylor",
]

DRUG_NAMES = [
    "Amoxicillin", "Lisinopril", "Metformin", "Atorvastatin",
    "Omeprazole", "Amlodipine", "Levothyroxine", "Metoprolol",
    "Ciprofloxacin", "Prednisone", "Ibuprofen", "Azithromycin",
    "Pantoprazole", "Losartan", "Gabapentin", "Sertraline",
    "Cephalexin", "Doxycycline", "Furosemide", "Clindamycin",
]

DOSAGES = [
    "250mg", "500mg", "100mg", "200mg", "10mg", "20mg", "40mg",
    "5mg", "50mg", "75mg", "150mg", "300mg", "25mg", "80mg",
]

FREQUENCIES = [
    "Once daily", "Twice daily", "Three times daily", "BID",
    "TID", "QID", "Every 8 hours", "Every 12 hours",
    "Before meals", "After meals", "At bedtime",
]

DOCTOR_NAMES = [
    "Dr. A. Kumar", "Dr. S. Johnson", "Dr. R. Patel", "Dr. M. Williams",
    "Dr. J. Chen", "Dr. E. Brown", "Dr. K. Singh", "Dr. L. Anderson",
    "Dr. P. Garcia", "Dr. T. Nguyen", "Dr. D. Kim", "Dr. N. Davis",
]

DATES = [
    "2026-08-01", "2026-07-15", "2026-06-22", "2026-05-10",
    "2026-08-03", "2026-07-28", "2026-06-14", "2026-04-20",
    "2026-08-05", "2026-07-01", "2026-06-30", "2026-05-25",
]


def generate_sample_data() -> dict:
    """Generate a random prescription's ground-truth field values."""
    return {
        "patient_name": random.choice(PATIENT_NAMES),
        "drug_name": random.choice(DRUG_NAMES),
        "dosage": random.choice(DOSAGES),
        "frequency": random.choice(FREQUENCIES),
        "doctor_name": random.choice(DOCTOR_NAMES),
        "document_date": random.choice(DATES),
    }


def render_prescription(data: dict, font_path: str, font_size: int = 32) -> Image.Image:
    """
    Render a prescription image with handwriting-style font.

    Creates a realistic prescription layout with:
    - Clinic header (printed)
    - Patient info (handwritten)
    - Rx section with drug/dosage/frequency (handwritten)
    - Doctor signature line (handwritten)
    - Date (handwritten)
    """
    # Canvas size
    width, height = 800, 1000
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        hw_font = ImageFont.truetype(font_path, font_size)
        hw_font_large = ImageFont.truetype(font_path, font_size + 8)
        hw_font_small = ImageFont.truetype(font_path, font_size - 4)
    except Exception as e:
        print(f"Warning: Could not load font {font_path}: {e}")
        hw_font = ImageFont.load_default()
        hw_font_large = hw_font
        hw_font_small = hw_font

    # Use default font for printed header
    try:
        header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        header_font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except Exception:
        header_font = ImageFont.load_default()
        header_font_bold = header_font

    y = 30

    # --- Clinic header (printed text) ---
    draw.text((width // 2 - 120, y), "City Medical Center", fill="black", font=header_font_bold)
    y += 30
    draw.text((width // 2 - 140, y), "123 Healthcare Ave, Medical District", fill="gray", font=header_font)
    y += 22
    draw.text((width // 2 - 80, y), "Ph: 555-0123-4567", fill="gray", font=header_font)
    y += 40

    # Horizontal line
    draw.line([(40, y), (width - 40, y)], fill="black", width=2)
    y += 20

    # --- Date (handwritten) ---
    draw.text((width - 250, y), "Date: ", fill="black", font=header_font)
    draw.text((width - 200, y - 5), data["document_date"], fill="darkblue", font=hw_font)
    y += 15

    # --- Patient info (handwritten) ---
    draw.text((50, y), "Patient Name: ", fill="black", font=header_font)
    y += 5
    draw.text((190, y - 5), data["patient_name"], fill="darkblue", font=hw_font_large)
    y += 50

    # Horizontal line
    draw.line([(40, y), (width - 40, y)], fill="lightgray", width=1)
    y += 30

    # --- Rx symbol ---
    draw.text((50, y), "Rx", fill="black", font=hw_font_large)
    y += 60

    # --- Drug name (handwritten) ---
    draw.text((80, y), data["drug_name"], fill="darkblue", font=hw_font_large)
    y += 50

    # --- Dosage (handwritten) ---
    draw.text((80, y), data["dosage"], fill="darkblue", font=hw_font)
    y += 45

    # --- Frequency (handwritten) ---
    draw.text((80, y), data["frequency"], fill="darkblue", font=hw_font)
    y += 80

    # Horizontal line
    draw.line([(40, y), (width - 40, y)], fill="lightgray", width=1)
    y += 30

    # --- Doctor signature (handwritten) ---
    draw.text((50, y), "Doctor: ", fill="black", font=header_font)
    draw.text((130, y - 5), data["doctor_name"], fill="darkblue", font=hw_font)
    y += 50

    # Signature line
    draw.line([(400, y), (width - 60, y)], fill="black", width=1)
    draw.text((420, y + 5), "Signature", fill="gray", font=hw_font_small)

    return img


def apply_moderate_degradation(img: Image.Image) -> Image.Image:
    """Apply moderate degradation: slight blur, mild rotation, light noise."""
    # Slight rotation
    angle = random.uniform(-3, 3)
    img = img.rotate(angle, fillcolor="white", expand=False)

    # Light Gaussian blur
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Add light noise
    import numpy as np
    arr = np.array(img)
    noise = np.random.normal(0, 8, arr.shape).astype(np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    return img


def apply_heavy_degradation(img: Image.Image) -> Image.Image:
    """Apply heavy degradation: blur, rotation, low contrast, speckle noise."""
    # Rotation
    angle = random.uniform(-8, 8)
    img = img.rotate(angle, fillcolor="white", expand=False)

    # Reduce contrast
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(0.5)

    # Brightness reduction (simulates poor lighting)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.75)

    # Heavier Gaussian blur
    img = img.filter(ImageFilter.GaussianBlur(radius=2.0))

    # Speckle noise
    import numpy as np
    arr = np.array(img)
    noise = np.random.normal(0, 18, arr.shape).astype(np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # Slight yellowing (simulates aged paper)
    yellow_overlay = Image.new("RGB", img.size, (245, 240, 220))
    img = Image.blend(img, yellow_overlay, alpha=0.15)

    return img


def main():
    """Generate the full synthetic handwriting test set."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Verify fonts exist
    available_fonts = []
    for fp in FONT_FILES:
        if os.path.exists(fp):
            available_fonts.append(fp)
        else:
            print(f"Warning: Font not found: {fp}")

    if not available_fonts:
        print("Error: No fonts found. Please download cursive fonts to scripts/fonts/")
        print("Expected files: Caveat.ttf, HomemadeApple-Regular.ttf, ReenieBeanie-Regular.ttf")
        sys.exit(1)

    print(f"Found {len(available_fonts)} font(s): {[os.path.basename(f) for f in available_fonts]}")

    # Define samples: (count, tier_name, degradation_fn)
    tiers = [
        (8, "clean", None),
        (6, "moderate", apply_moderate_degradation),
        (6, "degraded", apply_heavy_degradation),
    ]

    sample_idx = 0
    manifest = []

    for count, tier_name, degrade_fn in tiers:
        print(f"\nGenerating {count} '{tier_name}' samples...")
        for i in range(count):
            sample_idx += 1
            font_path = random.choice(available_fonts)
            font_name = os.path.basename(font_path).replace(".ttf", "")

            data = generate_sample_data()

            # Render the prescription
            img = render_prescription(data, font_path, font_size=random.randint(28, 36))

            # Apply degradation if needed
            if degrade_fn:
                img = degrade_fn(img)

            # Save image
            img_filename = f"sample_{sample_idx:03d}_{tier_name}_{font_name}.png"
            img_path = os.path.join(OUTPUT_DIR, img_filename)
            img.save(img_path, "PNG")

            # Save ground truth
            gt_filename = f"sample_{sample_idx:03d}_{tier_name}_{font_name}.json"
            gt_path = os.path.join(OUTPUT_DIR, gt_filename)
            ground_truth = {
                "sample_id": sample_idx,
                "tier": tier_name,
                "font": font_name,
                "fields": data,
            }
            with open(gt_path, "w") as f:
                json.dump(ground_truth, f, indent=2)

            manifest.append({
                "sample_id": sample_idx,
                "tier": tier_name,
                "font": font_name,
                "image_file": img_filename,
                "ground_truth_file": gt_filename,
            })

            print(f"  [{sample_idx:03d}] {tier_name}/{font_name}: {data['patient_name']} - {data['drug_name']} {data['dosage']}")

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Generated {sample_idx} samples in {OUTPUT_DIR}")
    print(f"Manifest: {manifest_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible test set
    main()
