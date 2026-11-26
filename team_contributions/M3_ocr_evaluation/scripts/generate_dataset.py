"""
Dataset Generation Script for DocuFlow M3 OCR Evaluation.
Generates 30 synthetic documents across 6 quality categories from 5 base documents:
- text_pdfs (5)
- scanned_pdfs (5)
- clear_images (5)
- blurry_images (5)
- rotated_images (5)
- low_quality_images (5)

Also generates ground_truth.json and dataset_manifest.csv.
"""

import csv
import json
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "sample_dataset"

# 5 distinct base documents with realistic structured business fields
BASE_DOCUMENTS = [
    {
        "base_id": "BASE_001",
        "doc_type": "Commercial Invoice",
        "company_name": "Apex Global Logistics Ltd",
        "name": "Sarah Jenkins",
        "invoice_number": "INV-2026-101",
        "date": "2026-10-14",
        "due_date": "2026-11-14",
        "email": "sarah.jenkins@example.com",
        "phone": "+1-555-0142",
        "total": "1250.00",
        "tax": "125.00",
        "currency": "USD",
        "items": [
            ("Air Freight Shipping Services", "1", "850.00"),
            ("Customs Clearance & Handling", "1", "400.00"),
        ]
    },
    {
        "base_id": "BASE_002",
        "doc_type": "Purchase Invoice",
        "company_name": "Summit Enterprise Solutions",
        "name": "Marcus Vance",
        "invoice_number": "INV-2026-102",
        "date": "2026-10-18",
        "due_date": "2026-11-18",
        "email": "m.vance@example.org",
        "phone": "+1-555-0198",
        "total": "4890.50",
        "tax": "489.05",
        "currency": "USD",
        "items": [
            ("Enterprise Software Subscription Q4", "1", "3500.00"),
            ("Technical Implementation & Setup", "1", "1390.50"),
        ]
    },
    {
        "base_id": "BASE_003",
        "doc_type": "Service Invoice",
        "company_name": "Horizon Creative Agency",
        "name": "Elena Rostova",
        "invoice_number": "INV-2026-103",
        "date": "2026-10-22",
        "due_date": "2026-11-22",
        "email": "elena.rostova@example.net",
        "phone": "+1-555-0284",
        "total": "750.25",
        "tax": "75.00",
        "currency": "USD",
        "items": [
            ("Brand Identity Redesign Package", "1", "550.25"),
            ("Digital Asset Optimization", "1", "200.00"),
        ]
    },
    {
        "base_id": "BASE_004",
        "doc_type": "Commercial Invoice",
        "company_name": "Nordic Clean Energy Corp",
        "name": "David Lindqvist",
        "invoice_number": "INV-2026-104",
        "date": "2026-10-25",
        "due_date": "2026-11-25",
        "email": "david.l@example.com",
        "phone": "+1-555-0371",
        "total": "9200.00",
        "tax": "920.00",
        "currency": "USD",
        "items": [
            ("Industrial Solar Inverter Unit", "2", "6400.00"),
            ("On-site Grid Commissioning", "1", "2800.00"),
        ]
    },
    {
        "base_id": "BASE_005",
        "doc_type": "Receipt",
        "company_name": "Cascade IT Solutions",
        "name": "Rachel Thorne",
        "invoice_number": "INV-2026-105",
        "date": "2026-10-29",
        "due_date": "2026-11-29",
        "email": "rachel.thorne@example.org",
        "phone": "+1-555-0459",
        "total": "320.00",
        "tax": "32.00",
        "currency": "USD",
        "items": [
            ("Cloud Infrastructure Audit", "1", "220.00"),
            ("Security Vulnerability Scan", "1", "100.00"),
        ]
    },
]

def render_document_image(base: dict, width: int = 1200, height: int = 1600) -> Image.Image:
    """Render a clean, high-resolution document image with structured text."""
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Use default bitmap font
    # In Windows, we can use default font or standard TTF fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 40)
        font_header = ImageFont.truetype("arialbd.ttf", 26)
        font_body = ImageFont.truetype("arial.ttf", 22)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
    except IOError:
        font_title = ImageFont.load_default()
        font_header = font_title
        font_body = font_title
        font_bold = font_title

    # Header banner
    draw.rectangle([(50, 40), (width - 50, 140)], fill=(240, 244, 248), outline=(200, 210, 220), width=2)
    draw.text((70, 60), base["company_name"], fill=(15, 30, 60), font=font_title)
    draw.text((70, 105), f"{base['doc_type'].upper()} — OFFICIAL RECORD", fill=(70, 90, 120), font=font_body)

    # Meta Section: Left column (Customer), Right column (Invoice metadata)
    draw.text((70, 170), "BILL TO:", fill=(15, 30, 60), font=font_header)
    draw.text((70, 210), f"Name: {base['name']}", fill=(20, 20, 20), font=font_bold)
    draw.text((70, 245), f"Email: {base['email']}", fill=(40, 40, 40), font=font_body)
    draw.text((70, 280), f"Phone: {base['phone']}", fill=(40, 40, 40), font=font_body)

    draw.text((650, 170), "INVOICE DETAILS:", fill=(15, 30, 60), font=font_header)
    # Using explicit labelled line formats that DocuFlow processors match
    draw.text((650, 210), f"Invoice Number: {base['invoice_number']}", fill=(20, 20, 20), font=font_bold)
    draw.text((650, 245), f"Date: {base['date']}", fill=(20, 20, 20), font=font_bold)
    draw.text((650, 280), f"Due Date: {base['due_date']}", fill=(40, 40, 40), font=font_body)
    draw.text((650, 315), f"Currency: {base['currency']}", fill=(40, 40, 40), font=font_body)

    # Dividing line
    draw.line([(70, 370), (width - 70, 370)], fill=(180, 190, 205), width=2)

    # Line Items Header
    draw.rectangle([(70, 390), (width - 70, 435)], fill=(230, 238, 246))
    draw.text((90, 402), "Description", fill=(15, 30, 60), font=font_header)
    draw.text((750, 402), "Qty", fill=(15, 30, 60), font=font_header)
    draw.text((950, 402), "Amount (USD)", fill=(15, 30, 60), font=font_header)

    y = 455
    for desc, qty, amt in base["items"]:
        draw.text((90, y), desc, fill=(30, 30, 30), font=font_body)
        draw.text((760, y), qty, fill=(30, 30, 30), font=font_body)
        draw.text((960, y), amt, fill=(30, 30, 30), font=font_body)
        y += 45
        draw.line([(70, y), (width - 70, y)], fill=(235, 235, 235), width=1)
        y += 15

    # Summary box
    box_top = y + 40
    draw.rectangle([(600, box_top), (width - 70, box_top + 160)], fill=(248, 250, 252), outline=(210, 220, 230), width=1)
    draw.text((630, box_top + 20), f"Tax Amount: {base['tax']}", fill=(60, 60, 60), font=font_body)
    draw.line([(630, box_top + 65), (width - 100, box_top + 65)], fill=(220, 220, 220), width=1)
    draw.text((630, box_top + 85), f"Total: {base['total']}", fill=(15, 30, 60), font=font_header)
    draw.text((630, box_top + 120), f"Payment Status: Outstanding", fill=(90, 100, 110), font=font_body)

    # Footer note
    draw.line([(70, height - 120), (width - 70, height - 120)], fill=(200, 210, 220), width=1)
    draw.text((70, height - 90), "Thank you for your business. For questions, contact support@docuflow.local", fill=(120, 130, 140), font=font_body)
    draw.text((70, height - 60), "DocuFlow Synthetic Evaluation Document — Strictly Fictional Data", fill=(160, 160, 160), font=font_body)

    return image

def generate_text_pdf(base: dict, output_path: Path):
    """Generate a digital PDF with selectable and extractable text layer using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    # Banner
    c.setFillColor(colors.HexColor("#F0F4F8"))
    c.rect(40, height - 110, width - 80, 70, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0F1E3C"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(55, height - 70, base["company_name"])
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#465A78"))
    c.drawString(55, height - 95, f"{base['doc_type'].upper()} — OFFICIAL RECORD")

    # Metadata
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0F1E3C"))
    c.drawString(55, height - 140, "BILL TO:")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#141414"))
    c.drawString(55, height - 165, f"Name: {base['name']}")
    c.drawString(55, height - 185, f"Email: {base['email']}")
    c.drawString(55, height - 205, f"Phone: {base['phone']}")

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0F1E3C"))
    c.drawString(330, height - 140, "INVOICE DETAILS:")
    c.setFont("Helvetica", 11)
    c.drawString(330, height - 165, f"Invoice Number: {base['invoice_number']}")
    c.drawString(330, height - 185, f"Date: {base['date']}")
    c.drawString(330, height - 205, f"Due Date: {base['due_date']}")
    c.drawString(330, height - 225, f"Currency: {base['currency']}")

    # Table Header
    c.setFillColor(colors.HexColor("#E6EEF6"))
    c.rect(40, height - 270, width - 80, 25, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0F1E3C"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, height - 263, "Description")
    c.drawString(380, height - 263, "Qty")
    c.drawString(480, height - 263, "Amount (USD)")

    y = height - 295
    c.setFont("Helvetica", 10)
    for desc, qty, amt in base["items"]:
        c.drawString(55, y, desc)
        c.drawString(385, y, qty)
        c.drawString(485, y, amt)
        y -= 25

    # Total Box
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(330, y - 65, width - 370, 70, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#0F1E3C"))
    c.setFont("Helvetica", 10)
    c.drawString(345, y - 20, f"Tax Amount: {base['tax']}")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(345, y - 45, f"Total: {base['total']}")

    # Footer
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#78828C"))
    c.drawString(55, 60, "Thank you for your business. For questions, contact support@docuflow.local")
    c.drawString(55, 45, "DocuFlow Synthetic Evaluation Document — Strictly Fictional Data")

    c.save()

def generate_scanned_pdf(base_image: Image.Image, output_path: Path):
    """Generate scanned PDF containing only the raster image with no text layer."""
    # Convert image to PDF via PIL (pure raster PDF)
    base_image.save(output_path, "PDF", resolution=150.0)

def main():
    random.seed(42)
    categories = [
        "text_pdfs",
        "scanned_pdfs",
        "clear_images",
        "blurry_images",
        "rotated_images",
        "low_quality_images"
    ]
    for cat in categories:
        (DATASET_DIR / cat).mkdir(parents=True, exist_ok=True)

    ground_truth = []
    manifest_rows = []

    doc_counter = 1

    # Base images cache
    base_images = {base["base_id"]: render_document_image(base) for base in BASE_DOCUMENTS}

    # 1. Text-based PDFs (5)
    for base in BASE_DOCUMENTS:
        doc_id = f"DOC_{doc_counter:03d}"
        doc_counter += 1
        filename = f"{base['base_id'].lower()}_text.pdf"
        out_path = DATASET_DIR / "text_pdfs" / filename
        generate_text_pdf(base, out_path)

        meta = {
            "document_id": doc_id,
            "base_id": base["base_id"],
            "file_name": filename,
            "category": "text_pdfs",
            "format": "PDF",
            "doc_type": base["doc_type"],
            "company_name": base["company_name"],
            "expected_fields": {
                "name": base["name"],
                "date": base["date"],
                "invoice_number": base["invoice_number"],
                "total": base["total"],
                "due_date": base["due_date"],
                "email": base["email"],
                "phone": base["phone"],
                "tax": base["tax"],
                "currency": base["currency"],
            },
            "transformations": "Native vector PDF with selectable text",
        }
        ground_truth.append(meta)
        manifest_rows.append([
            doc_id, f"sample_dataset/text_pdfs/{filename}", base["doc_type"],
            "text_pdfs", "PDF", "Vector", 1, "Native digital text layer"
        ])

    # 2. Scanned PDFs (5)
    for base in BASE_DOCUMENTS:
        doc_id = f"DOC_{doc_counter:03d}"
        doc_counter += 1
        filename = f"{base['base_id'].lower()}_scanned.pdf"
        out_path = DATASET_DIR / "scanned_pdfs" / filename
        img = base_images[base["base_id"]]
        generate_scanned_pdf(img, out_path)

        meta = {
            "document_id": doc_id,
            "base_id": base["base_id"],
            "file_name": filename,
            "category": "scanned_pdfs",
            "format": "PDF",
            "doc_type": base["doc_type"],
            "company_name": base["company_name"],
            "expected_fields": {
                "name": base["name"],
                "date": base["date"],
                "invoice_number": base["invoice_number"],
                "total": base["total"],
                "due_date": base["due_date"],
                "email": base["email"],
                "phone": base["phone"],
                "tax": base["tax"],
                "currency": base["currency"],
            },
            "transformations": "Raster image-only PDF (no text stream)",
        }
        ground_truth.append(meta)
        manifest_rows.append([
            doc_id, f"sample_dataset/scanned_pdfs/{filename}", base["doc_type"],
            "scanned_pdfs", "PDF", "1200x1600", 1, "Raster image-only PDF, requires OCR"
        ])

    # 3. Clear Images (5)
    for base in BASE_DOCUMENTS:
        doc_id = f"DOC_{doc_counter:03d}"
        doc_counter += 1
        filename = f"{base['base_id'].lower()}_clear.png"
        out_path = DATASET_DIR / "clear_images" / filename
        img = base_images[base["base_id"]]
        img.save(out_path, "PNG")

        meta = {
            "document_id": doc_id,
            "base_id": base["base_id"],
            "file_name": filename,
            "category": "clear_images",
            "format": "PNG",
            "doc_type": base["doc_type"],
            "company_name": base["company_name"],
            "expected_fields": {
                "name": base["name"],
                "date": base["date"],
                "invoice_number": base["invoice_number"],
                "total": base["total"],
                "due_date": base["due_date"],
                "email": base["email"],
                "phone": base["phone"],
                "tax": base["tax"],
                "currency": base["currency"],
            },
            "transformations": "High resolution, sharp PNG",
        }
        ground_truth.append(meta)
        manifest_rows.append([
            doc_id, f"sample_dataset/clear_images/{filename}", base["doc_type"],
            "clear_images", "PNG", "1200x1600", 1, "High-contrast clean image"
        ])

    # 4. Blurry Images (5)
    blur_radii = [1.5, 2.5, 3.5, 4.5, 5.5]
    for idx, base in enumerate(BASE_DOCUMENTS):
        doc_id = f"DOC_{doc_counter:03d}"
        doc_counter += 1
        filename = f"{base['base_id'].lower()}_blurry.png"
        out_path = DATASET_DIR / "blurry_images" / filename
        radius = blur_radii[idx]
        img = base_images[base["base_id"]].filter(ImageFilter.GaussianBlur(radius=radius))
        img.save(out_path, "PNG")

        meta = {
            "document_id": doc_id,
            "base_id": base["base_id"],
            "file_name": filename,
            "category": "blurry_images",
            "format": "PNG",
            "doc_type": base["doc_type"],
            "company_name": base["company_name"],
            "expected_fields": {
                "name": base["name"],
                "date": base["date"],
                "invoice_number": base["invoice_number"],
                "total": base["total"],
                "due_date": base["due_date"],
                "email": base["email"],
                "phone": base["phone"],
                "tax": base["tax"],
                "currency": base["currency"],
            },
            "transformations": f"Gaussian Blur radius={radius}",
        }
        ground_truth.append(meta)
        manifest_rows.append([
            doc_id, f"sample_dataset/blurry_images/{filename}", base["doc_type"],
            "blurry_images", "PNG", "1200x1600", 1, f"Gaussian blur radius={radius}"
        ])

    # 5. Rotated Images (5) - 5, 15, 30, 90, 180 degrees
    rotation_angles = [5, 15, 30, 90, 180]
    for idx, base in enumerate(BASE_DOCUMENTS):
        doc_id = f"DOC_{doc_counter:03d}"
        doc_counter += 1
        filename = f"{base['base_id'].lower()}_rot{rotation_angles[idx]}.png"
        out_path = DATASET_DIR / "rotated_images" / filename
        angle = rotation_angles[idx]
        img = base_images[base["base_id"]].rotate(angle, expand=True, fillcolor=(255, 255, 255))
        img.save(out_path, "PNG")

        meta = {
            "document_id": doc_id,
            "base_id": base["base_id"],
            "file_name": filename,
            "category": "rotated_images",
            "format": "PNG",
            "doc_type": base["doc_type"],
            "company_name": base["company_name"],
            "expected_fields": {
                "name": base["name"],
                "date": base["date"],
                "invoice_number": base["invoice_number"],
                "total": base["total"],
                "due_date": base["due_date"],
                "email": base["email"],
                "phone": base["phone"],
                "tax": base["tax"],
                "currency": base["currency"],
            },
            "transformations": f"Counter-clockwise rotation {angle} degrees with white fill",
        }
        ground_truth.append(meta)
        manifest_rows.append([
            doc_id, f"sample_dataset/rotated_images/{filename}", base["doc_type"],
            "rotated_images", "PNG", f"{img.width}x{img.height}", 1, f"Rotated {angle} deg"
        ])

    # 6. Low-quality Images (5) - compression, downsampling, noise, contrast reduction
    degradations = [
        ("JPEG Quality 20", lambda im: degrade_jpeg(im, 20)),
        ("Downsample 3x then Upscale", lambda im: degrade_downsample(im, 3)),
        ("Salt & Pepper Noise", lambda im: degrade_noise(im, 0.05)),
        ("Low Contrast & Low Brightness", lambda im: degrade_contrast_brightness(im, 0.4, 0.7)),
        ("Combined JPEG 15 + Downsample 2x", lambda im: degrade_combined(im)),
    ]
    for idx, base in enumerate(BASE_DOCUMENTS):
        doc_id = f"DOC_{doc_counter:03d}"
        doc_counter += 1
        deg_name, deg_func = degradations[idx]
        ext = ".jpg" if "JPEG" in deg_name else ".png"
        filename = f"{base['base_id'].lower()}_lowqual_{idx+1}{ext}"
        out_path = DATASET_DIR / "low_quality_images" / filename
        deg_img = deg_func(base_images[base["base_id"]])
        if ext == ".jpg":
            deg_img.save(out_path, "JPEG", quality=20)
        else:
            deg_img.save(out_path, "PNG")

        meta = {
            "document_id": doc_id,
            "base_id": base["base_id"],
            "file_name": filename,
            "category": "low_quality_images",
            "format": ext.upper().replace(".", ""),
            "doc_type": base["doc_type"],
            "company_name": base["company_name"],
            "expected_fields": {
                "name": base["name"],
                "date": base["date"],
                "invoice_number": base["invoice_number"],
                "total": base["total"],
                "due_date": base["due_date"],
                "email": base["email"],
                "phone": base["phone"],
                "tax": base["tax"],
                "currency": base["currency"],
            },
            "transformations": deg_name,
        }
        ground_truth.append(meta)
        manifest_rows.append([
            doc_id, f"sample_dataset/low_quality_images/{filename}", base["doc_type"],
            "low_quality_images", ext.upper().replace(".", ""), f"{deg_img.width}x{deg_img.height}", 1, deg_name
        ])

    # Save ground_truth.json
    gt_path = DATASET_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # Save dataset_manifest.csv
    manifest_path = DATASET_DIR / "dataset_manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "document_id", "file_path", "document_type", "quality_category",
            "format", "resolution", "page_count", "transformation_details"
        ])
        writer.writerows(manifest_rows)

    print(f"Generated {len(ground_truth)} evaluation documents across {len(categories)} categories.")
    print(f"Ground truth saved to: {gt_path}")
    print(f"Dataset manifest saved to: {manifest_path}")

def degrade_jpeg(image: Image.Image, quality: int) -> Image.Image:
    import io
    buf = io.BytesIO()
    image.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")

def degrade_downsample(image: Image.Image, factor: int) -> Image.Image:
    w, h = image.size
    small = image.resize((w // factor, h // factor), Image.Resampling.BILINEAR)
    return small.resize((w, h), Image.Resampling.NEAREST)

def degrade_noise(image: Image.Image, amount: float) -> Image.Image:
    im = image.copy()
    pixels = im.load()
    w, h = im.size
    num_noisy = int(amount * w * h)
    for _ in range(num_noisy):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        val = 0 if random.random() < 0.5 else 255
        pixels[x, y] = (val, val, val)
    return im

def degrade_contrast_brightness(image: Image.Image, contrast_factor: float, brightness_factor: float) -> Image.Image:
    from PIL import ImageEnhance
    enh_c = ImageEnhance.Contrast(image)
    im = enh_c.enhance(contrast_factor)
    enh_b = ImageEnhance.Brightness(im)
    return enh_b.enhance(brightness_factor)

def degrade_combined(image: Image.Image) -> Image.Image:
    down = degrade_downsample(image, 2)
    return degrade_jpeg(down, 15)

if __name__ == "__main__":
    main()
