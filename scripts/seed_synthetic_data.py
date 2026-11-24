"""Seed synthetic document files and database demo data for DocuFlow."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF
import pandas as pd
from PIL import Image, ImageDraw

from app.database import SessionLocal, Base, engine
from app.config import settings
from app.models.user import User, UserRole
from app.models.document import Document, UploadStatus
from app.models.job import ProcessingJob, JobStatus
from app.services.document_service import validate_file_content, calculate_sha256
from app.services.processing_service import ProcessingService


def create_sample_files():
    """Generate realistic synthetic documents for testing and evaluation."""
    os.makedirs("samples/pdfs", exist_ok=True)
    os.makedirs("samples/csv", exist_ok=True)
    os.makedirs("samples/excel", exist_ok=True)
    os.makedirs("samples/images", exist_ok=True)

    # 1. Synthetic PDF Invoice 1
    doc1 = fitz.open()
    page1 = doc1.new_page(width=595, height=842)
    invoice_1_text = """
    INVOICE
    Acme Industrial Supplies Inc.
    100 Enterprise Way, Suite 400
    San Francisco, CA 94105
    contact@acmesupplies.com | +1 (555) 234-5678

    Invoice Number: INV-2026-0042
    Invoice Date: 2026-03-15
    Due Date: 2026-04-15
    Status: UNPAID

    Billed To:
    TechNova Solutions Ltd.
    billing@technova.io
    
    Items:
    1. Cloud Infrastructure Consulting - $4,500.00
    2. High-Performance Server Rack - $2,200.00
    3. Network Switch 48-Port PoE - $850.00
    
    Subtotal: $7,550.00
    Tax (10%): $755.00
    Total Amount: $8,305.00 USD
    """
    page1.insert_text((50, 60), invoice_1_text, fontsize=11)
    pdf1_path = "samples/pdfs/sample_invoice_1.pdf"
    doc1.save(pdf1_path)
    doc1.close()

    # 2. Synthetic PDF Invoice 2
    doc2 = fitz.open()
    page2 = doc2.new_page(width=595, height=842)
    invoice_2_text = """
    TAX INVOICE
    Global Logistics & Freight Corp
    info@globallogistics.com | (800) 555-0199

    Invoice Number: GL-88491-A
    Invoice Date: 2026-02-28
    Due Date: 2026-03-30
    
    Customer: Apex Enterprises
    support@apex.com

    Services Rendered:
    - International Ocean Freight Shipment: $3,450.00
    - Customs Clearance Fee: $350.00
    - Warehouse Handling: $200.00

    Tax Amount: $400.00
    Total Amount: $4,400.00 USD
    """
    page2.insert_text((50, 60), invoice_2_text, fontsize=11)
    pdf2_path = "samples/pdfs/sample_invoice_2.pdf"
    doc2.save(pdf2_path)
    doc2.close()

    # 3. Synthetic CSV
    csv_data = [
        {"invoice_number": "INV-CSV-101", "invoice_date": "2026-01-10", "due_date": "2026-02-10", "company_name": "Atlas Cloud Inc", "email": "billing@atlascloud.com", "total_amount": 1250.00, "tax_amount": 125.00},
        {"invoice_number": "INV-CSV-102", "invoice_date": "2026-01-15", "due_date": "2026-02-15", "company_name": "Beacon Media LLC", "email": "accounts@beaconmedia.com", "total_amount": 3400.50, "tax_amount": 340.05},
        {"invoice_number": "INV-CSV-103", "invoice_date": "2026-01-20", "due_date": "2026-02-20", "company_name": "Crestview Partners", "email": "finance@crestview.org", "total_amount": 920.00, "tax_amount": 92.00},
    ]
    df_csv = pd.DataFrame(csv_data)
    csv_path = "samples/csv/sample_invoices.csv"
    df_csv.to_csv(csv_path, index=False)

    # 4. Synthetic Excel
    excel_data = [
        {"invoice_number": "XLS-9001", "invoice_date": "2026-02-01", "due_date": "2026-03-01", "company_name": "Delta Dynamics", "email": "pay@deltadyn.com", "total_amount": 5400.00, "tax_amount": 540.00},
        {"invoice_number": "XLS-9002", "invoice_date": "2026-02-05", "due_date": "2026-03-05", "company_name": "Echo Wave Telecom", "email": "finance@echowave.net", "total_amount": 1850.75, "tax_amount": 185.08},
    ]
    df_excel = pd.DataFrame(excel_data)
    excel_path = "samples/excel/sample_payroll.xlsx"
    df_excel.to_excel(excel_path, index=False, engine="openpyxl")

    # 5. Synthetic PNG Receipt
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "RECEIPT / INVOICE", fill=(0, 0, 0))
    draw.text((30, 70), "Store: QuickMart Retail Store #14", fill=(0, 0, 0))
    draw.text((30, 110), "Invoice Number: REC-2026-778", fill=(0, 0, 0))
    draw.text((30, 150), "Date: 2026-03-10", fill=(0, 0, 0))
    draw.text((30, 190), "Email: receipts@quickmart.com", fill=(0, 0, 0))
    draw.text((30, 230), "Total Amount: $148.50 USD", fill=(0, 0, 0))
    img_path = "samples/images/sample_receipt.png"
    img.save(img_path)

    print("Sample synthetic files created:")
    print(f"  - {pdf1_path}")
    print(f"  - {pdf2_path}")
    print(f"  - {csv_path}")
    print(f"  - {excel_path}")
    print(f"  - {img_path}")


def _save_and_process_sample(db, admin_id, file_path, orig_name):
    with open(file_path, "rb") as f:
        content = f.read()

    canonical_type = validate_file_content(orig_name, content)
    checksum = calculate_sha256(content)

    ext = Path(orig_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    storage_path = settings.uploads_path / stored_name
    with open(storage_path, "wb") as f:
        f.write(content)

    doc = Document(
        uploaded_by=admin_id,
        original_filename=orig_name,
        stored_filename=stored_name,
        file_type=canonical_type,
        file_size=len(content),
        checksum=checksum,
        storage_reference=str(storage_path),
        upload_status=UploadStatus.STORED
    )
    db.add(doc)
    db.flush()

    job = ProcessingJob(
        document_id=doc.id,
        created_by=admin_id,
        processing_type="auto",
        status=JobStatus.QUEUED
    )
    db.add(job)
    db.commit()

    service = ProcessingService(db)
    completed_job = service.execute_job(job.id)
    print(f"Document {orig_name} (ID: {doc.id}) -> Job {completed_job.id} Status: {completed_job.status.value}")


def seed_db_with_samples():
    """Upload and process sample documents into database for immediate live demonstration."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin:
            print("No admin user found. Run scripts/init_db.py first.")
            return

        _save_and_process_sample(db, admin.id, "samples/pdfs/sample_invoice_1.pdf", "sample_invoice_1.pdf")
        _save_and_process_sample(db, admin.id, "samples/csv/sample_invoices.csv", "sample_invoices.csv")
        _save_and_process_sample(db, admin.id, "samples/excel/sample_payroll.xlsx", "sample_payroll.xlsx")

        print("Database successfully seeded with live document processing data.")
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_files()
    seed_db_with_samples()
