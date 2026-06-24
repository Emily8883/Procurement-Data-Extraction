"""
Test Data Generator for Procurement Pipeline Validation

Generates realistic test PDFs simulating:
- Invoice documents (clear, varied formats)
- Scanned documents (degraded quality, OCR challenges)
- Specification sheets (technical data, tables)
- Edge cases (corrupted, rotated, multi-language)
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import random
import hashlib
import sys

# CRITICAL: Avoid importing at module level to prevent namespace collision
# No PDF libraries imported - using text files instead for simplicity
HAS_REPORTLAB = False
HAS_PIL = False


class TestDataGenerator:
    """Generates test PDF files with realistic content"""
    
    def __init__(self, output_dir="testing/test_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.invoice_count = 0
        self.scanned_count = 0
        self.spec_count = 0
        self.edge_case_count = 0
        
        # Spanish terms for multi-language testing
        self.spanish_terms = {
            "Invoice": "Factura",
            "Number": "Número",
            "Date": "Fecha",
            "Description": "Descripción",
            "Quantity": "Cantidad",
            "Price": "Precio",
            "Total": "Total",
            "Amount": "Importe",
            "Currency": "Moneda"
        }
        
    def generate_invoice_text(self, invoice_num, use_spanish=False):
        """Generate invoice text content"""
        date_str = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        supplier = random.choice([
            "TechSupply Inc.",
            "Global Materials Ltd.",
            "Industrial Solutions Corp.",
            "Premium Parts Co."
        ])
        
        currency = random.choice(["USD", "EUR", "GBP"])
        qty = random.randint(1, 100)
        unit_price = round(random.uniform(10, 5000), 2)
        total = qty * unit_price
        
        if use_spanish:
            text = f"""
{self.spanish_terms['Invoice']} #{invoice_num}

{self.spanish_terms['Date']}: {date_str}
{self.spanish_terms['Number']}: INV-{invoice_num}

Proveedor: {supplier}

{self.spanish_terms['Description']}: Suministro industrial
{self.spanish_terms['Quantity']}: {qty}
{self.spanish_terms['Price']}: {unit_price} {currency}
{self.spanish_terms['Total']}: {total} {currency}

Vencimiento: {due_date}
"""
        else:
            text = f"""
INVOICE #{invoice_num}

Date: {date_str}
Invoice Number: INV-{invoice_num}

Supplier: {supplier}

Description: Industrial Supplies
Quantity: {qty}
Unit Price: {unit_price} {currency}
Total Amount: {total} {currency}

Due Date: {due_date}
"""
        return text
    
    def create_text_pdf(self, filename, content):
        """Create simple text-based PDF (fallback if reportlab not available)"""
        filepath = self.output_dir / filename
        
        # Simple text file as fallback (will be treated as text extraction)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    def create_pdf_with_reportlab(self, filename, content):
        """Create PDF using reportlab if available"""
        if not HAS_REPORTLAB:
            return self.create_text_pdf(filename, content)
        
        filepath = self.output_dir / filename
        
        c = canvas.Canvas(str(filepath), pagesize=letter)
        width, height = letter
        
        # Add simple header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, "PROCUREMENT DOCUMENT")
        
        # Add content
        c.setFont("Helvetica", 10)
        y_position = height - 100
        line_height = 14
        
        for line in content.split('\n'):
            if y_position < 50:
                c.showPage()
                y_position = height - 50
            c.drawString(50, y_position, line.strip()[:80])  # Limit line length
            y_position -= line_height
        
        c.save()
        return str(filepath)
    
    def generate_clean_invoices(self, count=20):
        """Generate clean, well-formatted invoices"""
        print(f"Generating {count} clean invoices...")
        
        for i in range(count):
            invoice_num = f"2024{i+1:04d}"
            content = self.generate_invoice_text(invoice_num, use_spanish=(i % 4 == 0))
            
            filename = f"invoice_clean_{i+1:02d}.txt"
            self.create_pdf_with_reportlab(filename, content)
            
            self.invoice_count += 1
            if (i + 1) % 5 == 0:
                print(f"  ✓ Generated {i+1}/{count} clean invoices")
        
        print(f"✅ Generated {count} clean invoices")
        return self.invoice_count
    
    def generate_scanned_degraded(self, count=10):
        """Generate low-quality scanned documents"""
        print(f"Generating {count} low-quality scanned documents...")
        
        for i in range(count):
            invoice_num = f"2024{5000+i:04d}"
            content = self.generate_invoice_text(invoice_num)
            
            # Add degradation markers
            degraded = self._degrade_text(content)
            
            filename = f"invoice_scanned_{i+1:02d}.txt"
            self.create_text_pdf(filename, degraded)
            
            self.scanned_count += 1
            if (i + 1) % 5 == 0:
                print(f"  ✓ Generated {i+1}/{count} scanned documents")
        
        print(f"✅ Generated {count} low-quality scanned documents")
        return self.scanned_count
    
    def _degrade_text(self, text):
        """Simulate OCR degradation"""
        # Replace some characters with similar-looking ones
        replacements = {
            '0': 'O',
            'I': 'l',
            'S': '5',
            '8': 'B',
            '1': 'l'
        }
        
        degraded = text
        for orig, replacement in replacements.items():
            if random.random() < 0.3:  # 30% chance of degradation
                degraded = degraded.replace(orig, replacement)
        
        # Add noise
        lines = degraded.split('\n')
        noisy_lines = []
        for line in lines:
            if random.random() < 0.2:  # 20% chance of line noise
                # Skip line or add extra characters
                if random.random() < 0.5:
                    continue  # Skip line
                else:
                    line += " %%%% @@@"  # Add noise
            noisy_lines.append(line)
        
        return '\n'.join(noisy_lines)
    
    def generate_specification_sheets(self, count=10):
        """Generate specification sheet documents"""
        print(f"Generating {count} specification sheets...")
        
        for i in range(count):
            content = self._generate_spec_content(i)
            filename = f"specification_{i+1:02d}.txt"
            self.create_text_pdf(filename, content)
            
            self.spec_count += 1
            if (i + 1) % 5 == 0:
                print(f"  ✓ Generated {i+1}/{count} specification sheets")
        
        print(f"✅ Generated {count} specification sheets")
        return self.spec_count
    
    def _generate_spec_content(self, index):
        """Generate technical specification content"""
        part_numbers = [f"PART-{random.randint(10000, 99999)}" for _ in range(3)]
        
        content = f"""
TECHNICAL SPECIFICATION SHEET

Document ID: SPEC-{index+1:04d}
Date: {datetime.now().strftime('%Y-%m-%d')}
Revision: {random.randint(1, 5)}

PRODUCT SPECIFICATIONS

Part Number: {part_numbers[0]}
Description: Industrial Component
Specifications:
  - Dimensions: {random.randint(100, 500)}mm x {random.randint(50, 300)}mm
  - Weight: {random.uniform(0.5, 50):.2f} kg
  - Material: {random.choice(['Steel', 'Aluminum', 'Stainless Steel', 'Composite'])}
  - Temperature Range: {random.randint(-40, 0)}°C to {random.randint(60, 150)}°C
  - Pressure Rating: {random.randint(100, 1000)} PSI

SHIPPING INFORMATION

Weight: {random.uniform(1, 100):.2f} kg
Dimensions: {random.randint(20, 100)} x {random.randint(20, 100)} x {random.randint(20, 100)} cm
Packaging: Standard

SUPPLIER DETAILS

Name: {random.choice(['Supplier A', 'Supplier B', 'Supplier C'])}
Lead Time: {random.randint(7, 90)} days
"""
        return content
    
    def generate_edge_cases(self):
        """Generate edge case test files"""
        print("Generating edge case test files...")
        
        # Missing fields
        missing_fields = """
INVOICE
Date: 2024-06-24
Description: Component

Quantity: 50
"""
        self.create_text_pdf("edge_missing_fields.txt", missing_fields)
        self.edge_case_count += 1
        
        # Corrupted/garbled content
        corrupted = """
ÌÑVØÌÇÉ #2024001
Dåté: ¿¿¿¿-¿¿-¿¿
ÍNV-2024001

Súppléér: Undefined™
Dëscríptîøn: ???????
Quântîty: %%%
Príçé: @@@
Totâl: &&&
"""
        self.create_text_pdf("edge_corrupted.txt", corrupted)
        self.edge_case_count += 1
        
        # Empty/minimal document
        minimal = "Document"
        self.create_text_pdf("edge_minimal.txt", minimal)
        self.edge_case_count += 1
        
        # Rotated scan simulation (text garbled)
        rotated = """tnemiruqer esolc A
:rebmunN
123456
:etaD
2024-06-24
:ytitnauQ
50
"""
        self.create_text_pdf("edge_rotated.txt", rotated)
        self.edge_case_count += 1
        
        # Multi-language mixed
        multilang = """
INVOICE 2024001 / FACTURA 2024001

Date: 2024-06-24 / Fecha: 2024-06-24

Supplier: TechSupply Inc. / Proveedor: TechSupply S.A.

Item Description / Descripción del Artículo: Industrial Component
Quantity / Cantidad: 100
Unit Price / Precio Unitario: 25.50 USD
Total / Total: 2550.00 USD

Vencimiento / Due Date: 2024-07-24
"""
        self.create_text_pdf("edge_multilingual.txt", multilang)
        self.edge_case_count += 1
        
        print(f"✅ Generated {self.edge_case_count} edge case test files")
        return self.edge_case_count
    
    def generate_all(self):
        """Generate complete test dataset"""
        print("\n" + "="*70)
        print("GENERATING TEST DATASET FOR VALIDATION")
        print("="*70 + "\n")
        
        self.generate_clean_invoices(20)
        self.generate_scanned_degraded(10)
        self.generate_specification_sheets(10)
        self.generate_edge_cases()
        
        total = self.invoice_count + self.scanned_count + self.spec_count + self.edge_case_count
        
        print("\n" + "="*70)
        print("TEST DATASET GENERATION COMPLETE")
        print("="*70)
        print(f"Clean Invoices:         {self.invoice_count}")
        print(f"Scanned Documents:      {self.scanned_count}")
        print(f"Specification Sheets:   {self.spec_count}")
        print(f"Edge Cases:             {self.edge_case_count}")
        print(f"TOTAL FILES:            {total}")
        print(f"Location:               {self.output_dir}")
        print("="*70 + "\n")
        
        return {
            "clean_invoices": self.invoice_count,
            "scanned_documents": self.scanned_count,
            "specification_sheets": self.spec_count,
            "edge_cases": self.edge_case_count,
            "total_files": total,
            "output_directory": str(self.output_dir)
        }


if __name__ == "__main__":
    generator = TestDataGenerator()
    result = generator.generate_all()
    
    # Save metadata
    metadata_file = generator.output_dir / "dataset_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Metadata saved to: {metadata_file}")
