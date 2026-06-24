# Procurement Data Validation Report

**Generated:** 2026-06-24 15:55:35

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Records** | 4 |
| **Valid Records** | 2/4 (50%) |
| **Total Errors** | 4 |
| **Total Warnings** | 15 |
| **Validation Pass Rate** | 50% |

## Validation Rules Applied

### 1. Field Completeness Check
- Critical fields checked: supplier, invoice_or_po_number, issue_date, total_amount
- Text-based documents: STRICT (all fields required)
- Scanned documents: LENIENT (fields expected but not required due to OCR limitations)

### 2. Math Consistency Check
- Rule: `subtotal + tax ≈ total_amount`
- Tolerance: ±5.0%
- Applied to: Text-based documents only

### 3. Line Item Validation
- Rule: `quantity × unit_price ≈ total_price`
- Tolerance: ±5.0%
- Metadata detection: Flags suspicious quantities (>10,000)

### 4. OCR Quality Check
- Confidence score assessment
- Garbled text detection
- Missing rows indication
- Applied to: Scanned documents only

---

## Detailed Results

### Document 1: 00c4e05f2d8e31c0-Copy.pdf

**Status:** ✅ VALID

**Type:** scanned
**Confidence:** 0%

**Warnings (6):**
- 🟡 Scanned: Missing field 'supplier' (expected)
- 🟡 Scanned: Missing field 'invoice_or_po_number' (expected)
- 🟡 Scanned: Missing field 'issue_date' (expected)
- 🟡 Scanned: Missing field 'total_amount' (expected)
- 🟡 Scanned document: No data extracted. OCR not available.
- 🟡 OCR: No extraction - confidence 0%

**Field Completeness:**
- ✗ supplier
- ✗ invoice_or_po_number
- ✗ issue_date
- ✗ total_amount
- ✗ line_items

**OCR Quality Issues:**
- Confidence score is 0% - no data extracted via OCR

---

### Document 2: 00c4e05f2d8e31c0.pdf

**Status:** ✅ VALID

**Type:** scanned
**Confidence:** 0%

**Warnings (6):**
- 🟡 Scanned: Missing field 'supplier' (expected)
- 🟡 Scanned: Missing field 'invoice_or_po_number' (expected)
- 🟡 Scanned: Missing field 'issue_date' (expected)
- 🟡 Scanned: Missing field 'total_amount' (expected)
- 🟡 Scanned document: No data extracted. OCR not available.
- 🟡 OCR: No extraction - confidence 0%

**Field Completeness:**
- ✗ supplier
- ✗ invoice_or_po_number
- ✗ issue_date
- ✗ total_amount
- ✗ line_items

**OCR Quality Issues:**
- Confidence score is 0% - no data extracted via OCR

---

### Document 3: 0c2f9fc842a866ee.pdf

**Status:** ❌ INVALID

**Type:** text
**Confidence:** 45%

**Errors (2):**
- 🔴 CRITICAL: Missing field 'issue_date'
- 🔴 CRITICAL: Missing field 'total_amount'

**Warnings (2):**
- 🟡 Cannot verify math: missing numeric values for subtotal/tax/total_amount
- 🟡 Line 12: Suspicious quantity (29783.0) - likely metadata not item quantity

**Field Completeness:**
- ✓ supplier
- ✓ invoice_or_po_number
- ✗ issue_date
- ✗ total_amount
- ✓ line_items

**Math Consistency:**
- ✗ Subtotal Match
- ✗ Line Item Accuracy

**Line Item Issues (14):**
- Line 1:  Por Ordenanza Nº 2537 del 14 de abril del 2023, 
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 2:  El Artículo 93 del Reglamento de Operación y Fun
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 3:  El Artículo 96 del Reglamento de Operación y Fun
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 4: 1 S600100040138 SERVICIO 01
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 5: • Limpieza de 80 ml. de canaleta de lluvia con la 
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 6: tipo TI 1107mm. x 11.80 ml.), que se encuentre fil
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 7: Av. Inca Garcilaso de la Vega 1348 – 4° piso - Lim
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 8: 1 | S600100040138 | MANTENIMIENTO CORRECTIVO DE
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 9: CANALETAS Y COBERTURA DE TECHOS | SERVICIO |  |  |
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 10: Calaminon tipo TI 1107mm. x 11.80 ml.), a ambos la
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 11: una altura de 25 m. aproximadamente. Además de con
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 12: 29783 de Seguridad y Salud en el Trabajo y demás d
  - Suspicious quantity: 29783.0 (may be article/regulation number)
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 14: acumulado equivalente a S/ 10 000.00 (Diez mil con
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 15: *Nota: Se precisa que de no presentar la documenta
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]

---

### Document 4: 0cca4ed1c20922e1.pdf

**Status:** ❌ INVALID

**Type:** text
**Confidence:** 45%

**Errors (2):**
- 🔴 CRITICAL: Missing field 'issue_date'
- 🔴 CRITICAL: Missing field 'total_amount'

**Warnings (1):**
- 🟡 Cannot verify math: missing numeric values for subtotal/tax/total_amount

**Field Completeness:**
- ✓ supplier
- ✓ invoice_or_po_number
- ✗ issue_date
- ✗ total_amount
- ✓ line_items

**Math Consistency:**
- ✗ Subtotal Match
- ✗ Line Item Accuracy

**Line Item Issues (15):**
- Line 1: La adquisición de SEMÁFORO LED DE TRÁFICO 1 X 12 i
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 2: La adquisición del SEMÁFORO LED DE TRÁFICO 1 X 12 
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 3: 01 SEMÁFORO LED DE TRÁFICO 1 X 12 in DE POLICARBON
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 4:  Las unidades ópticas para semáforos ciclistas te
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 5:  El periodo del reloj interno del semáforo contad
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 6:  Los rangos de temperatura de trabajo estarán ent
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 7: cable eléctrico interno (de fábrica) no será menor
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 8: electromagnética EN 50293:2012 o equivalente, aseg
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 9: 01 |  |  | SEMÁFORO LED DE TRÁFICO 1 X 12 in DE PO
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 10: establecidas por la Norma Europea: EN 12368- 2006 
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 11: las zonas admitidas para cada color en el diagrama
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 12:  Debe cumplir con las normas IPC 610 (Aceptabilid
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 13: 001 (soldadura y ensambles electrónicos), IPC 600 
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 14: la norma de resistencia al fuego UL94 HV o V0 o no
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]
- Line 15:  Año de fabricación: Mínimo 2022
  - Incomplete price data: missing one or more of [quantity, unit_price, total_price]

---

## Recommendations

### 🔴 Critical Issues (4)
- Review and correct 4 validation error(s) before proceeding
- Do NOT auto-correct - investigate root cause
- May require re-extraction or manual review

### 🟡 Warnings (15)
- 15 warning(s) detected
- Review for data quality issues
- May indicate incomplete OCR or missing fields

### ⚠️ Invalid Records (2)
- 2/4 record(s) require attention
- Success rate: 50%
