# Spanish Procurement Document - Regex Patterns Reference

## Overview
This document contains regex patterns to extract procurement data (Item ID, Description, Quantity, Unit) from Spanish documents.

---

## 1. ITEM ID EXTRACTION

### Pattern 1: Alphanumeric Reference Code
```regex
(?:REF|ART|COD|CÓDIGO|ID|Código|Artículo)[:\s-]+([A-Z0-9\-]{3,20})
```
**Matches:** `REF-001`, `ART-2024-001`, `CÓDIGO: ABC-123`
**Spanish terms:** REF, ART, COD, CÓDIGO, ID, Artículo

### Pattern 2: Simple Numeric ID
```regex
(?:^|\n)[\s]*(\d{3,10})[\s]+(?=[A-Z]|$)
```
**Matches:** Line starting with `001`, `10234`
**Use case:** When item ID is just a number at line start

### Pattern 3: Formatted Code (YYYY-NNNN-X)
```regex
(\d{4}[-/]\d{4}[-/][A-Z0-9])
```
**Matches:** `2024-0001-A`, `2024/0034/B`

### Pattern 4: SKU/EAN/UPC Format
```regex
(?:SKU|EAN|UPC)[:\s-]+([A-Z0-9\-]{5,25})
```
**Matches:** `SKU-001-XX`, `EAN: 5901234123457`

---

## 2. DESCRIPTION EXTRACTION

### Pattern 1: Description After ID (Auto-detection)
```regex
(?:^|[\n])[\s]*\d+[\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.]+?)(?=[\s]*\d+(?:\s*(?:u|un|unid|Ud|pcs|kg|l|ml|m|m²|m³))?[\s]*$)
```
**Matches:** Text between numeric ID and quantity
**Supports:** Spanish accented characters (á, é, í, ó, ú, ñ, ü)

### Pattern 2: Bulleted Description
```regex
(?:[-•*]|\d+\.|o\))\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)(?:\s+\d+(?:\s+(?:u|un|unid|Ud|kg|l|m))?)?$
```
**Matches:**
- `- Papel bond A4`
- `• Tóner laser`
- `1. Lápices de color`
- `o) Clasificador`

### Pattern 3: Labeled Description
```regex
(?:Descripción|DESCRIPCIÓN|Concepto|CONCEPTO)[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)(?:\n|$|[0-9])
```
**Matches:** `Descripción: Papel bond A4`, `CONCEPTO: Servicios de consultoría`
**Spanish labels:** Descripción, DESCRIPCIÓN, Concepto, CONCEPTO

---

## 3. QUANTITY EXTRACTION

### Pattern 1: Decimal Quantity (. or , separator)
```regex
(?:^|[\s])((?:\d+[.,]\d+|\d+))(?:\s*(?:u|un|unid|Ud|pcs|kg|l|ml|m|m²|m³|ud\.|uds\.))?
```
**Matches:** `500`, `10.5`, `100,50` (European format)

### Pattern 2: Bracketed Quantity
```regex
[(\[](\d+(?:[.,]\d+)?)[)\]]
```
**Matches:** `(500)`, `[10.5]`, `[100,50]`

### Pattern 3: Labeled Quantity
```regex
(?:Cantidad|CANTIDAD|Qty|QTY|Cant\.)[:\s]+(\d+(?:[.,]\d+)?)
```
**Matches:** `Cantidad: 500`, `Qty: 10.5`, `Cant.: 100`
**Spanish labels:** Cantidad, CANTIDAD, Qty, QTY, Cant.

### Pattern 4: Quantity Before Unit
```regex
(\d+(?:[.,]\d+)?)\s+(?:u|un|unid|Ud|pcs|pz|kg|g|l|ml|m|m²|m³|ud\.|uds\.)
```
**Matches:** `500 u`, `10.5 kg`, `100 pz`

---

## 4. UNIT EXTRACTION

### Available Units by Category

#### Pieces / Units
```regex
(?:u|un|unidad|unidades|pz|pza|piezas|ud|uds|u\.)
```
- `u` - short for unidad
- `un` - alternative
- `unidad` / `unidades` - full words
- `pz` / `pza` / `piezas` - pieces
- `ud` / `uds` - Spanish abbreviation
- `u.` - with period

#### Weight
```regex
(?:kg|g|mg|gr|gramo|kilogramo|tonelada|ton|t)
```
- `kg` - kilograms
- `g` - grams
- `mg` - milligrams
- `gr` - grams (alternative)
- `tonelada` / `ton` / `t` - metric tons

#### Volume
```regex
(?:l|ml|litro|mililitro|m³|litros)
```
- `l` - liters
- `ml` - milliliters
- `m³` - cubic meters
- `litro` / `litros` / `mililitro` - full words

#### Length
```regex
(?:m|cm|mm|metro|centímetro|milímetro|km)
```
- `m` - meters
- `cm` - centimeters
- `mm` - millimeters
- `km` - kilometers

#### Area
```regex
(?:m²|cm²|hectárea|ha)
```
- `m²` - square meters
- `cm²` - square centimeters
- `hectárea` / `ha` - hectares

#### Container/Packaging
```regex
(?:caja|cajas|cj|cx|pack|paquete|lote|rollo|rollos|juego|set|kit)
```
- `caja` / `cajas` - boxes
- `pack` / `paquete` - packages
- `lote` - batch/lot
- `rollo` / `rollos` - rolls
- `juego` / `set` / `kit` - sets/kits

#### Time-based
```regex
(?:hora|horas|h|día|días)
```
- `hora` / `horas` / `h` - hours
- `día` / `días` - days

#### Services
```regex
(?:servicio|servicios)
```
- `servicio` / `servicios` - services

### Combined Unit Pattern (All Units)
```regex
(?:u|un|unidad|unidades|pz|pza|piezas|ud|uds|u\.|kg|g|mg|gr|gramo|kilogramo|tonelada|ton|t|l|ml|litro|mililitro|m³|litros|m|cm|mm|metro|centímetro|milímetro|km|m²|cm²|hectárea|ha|caja|cajas|cj|cx|pack|paquete|lote|rollo|rollos|juego|set|kit|hora|horas|h|día|días|servicio|servicios)
```

### Unit After Quantity Pattern
```regex
\d+(?:[.,]\d+)?\s+(u|un|unidad|...|servicios)
```
Extracts unit immediately following a quantity

---

## 5. COMPLETE LINE PATTERNS

### Pattern 1: Pipe-Separated (|)
```regex
(\d+)\s*\|\s*([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)\s*\|\s*(\d+(?:[.,]\d+)?)\s*\|\s*(u|un|...|servicios)
```
**Format:** `1 | Papel bond A4 | 500 | u`

### Pattern 2: Tab-Separated (\t)
```regex
(\d+)\t+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)\t+(\d+(?:[.,]\d+)?)\t+(u|un|...|servicios)
```
**Format:** `1	Papel bond A4	500	u`

### Pattern 3: Space-Separated
```regex
^(\d{1,5})\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]{5,100}?)\s+(\d+(?:[.,]\d+)?)\s+(u|un|...|servicios)$
```
**Format:** `1 Papel bond A4 500 u`

### Pattern 4: With Item Code
```regex
(?:REF|ART|COD)[:\s-]+([A-Z0-9\-]+)\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)\s+(\d+(?:[.,]\d+)?)\s+(u|un|...|servicios)
```
**Format:** `REF-001 Papel bond A4 500 u`

---

## 6. COMMON SPANISH PROCUREMENT TERMS

| English | Spanish | Abbreviation |
|---------|---------|--------------|
| Item | Artículo | Art. |
| Reference | Referencia | Ref. |
| Description | Descripción | Desc. |
| Concept/Item | Concepto | - |
| Quantity | Cantidad | Cant. |
| Unit | Unidad | Ud. |
| Code | Código | Cod. |
| Purchase Order | Orden de Compra | OC |
| Invoice | Factura | Fact. |
| Price | Precio | Prc. |

---

## 7. USAGE IN PYTHON

### Simple Usage
```python
import re

# Extract quantity
text = "Cantidad: 500 unidades"
match = re.search(r'(?:Cantidad|CANTIDAD)[:\s]+(\d+(?:[.,]\d+)?)', text, re.IGNORECASE)
if match:
    quantity = float(match.group(1).replace(',', '.'))
```

### With the Provided Extractor Class
```python
from spanish_procurement_regex import ProcurementExtractor

extractor = ProcurementExtractor()

# Extract all items from text
items = extractor.extract_complete_items(document_text)

for item in items:
    print(f"ID: {item['id']}")
    print(f"Description: {item['description']}")
    print(f"Quantity: {item['quantity']}")
    print(f"Unit: {item['unit']}")
```

---

## 8. TIPS FOR BEST RESULTS

1. **Normalize text first:**
   - Remove extra whitespace: `re.sub(r'\s+', ' ', text)`
   - Convert to consistent case for units (lowercase): `text.lower()`

2. **Handle decimal separators:**
   - Spanish uses both `.` and `,` for decimals
   - Always replace `,` with `.` before converting to float: `value.replace(',', '.')`

3. **For OCR'd text:**
   - Add flexibility with `\s+` for variable spacing
   - Consider using `re.IGNORECASE` flag
   - Clean up artifacts before regex matching

4. **Combining patterns:**
   - Try more specific patterns first (pipe-separated)
   - Fall back to more flexible patterns (space-separated)
   - Stop after first match to avoid duplicate extraction

5. **Testing:**
   - Test each pattern against actual sample data
   - Adjust character classes if documents use different format
   - Use `re.search()` for finding anywhere in text
   - Use `re.match()` for matching at start of string

---

## 9. REGEX FLAGS REFERENCE

```python
re.IGNORECASE  # Case-insensitive matching
re.MULTILINE   # ^ and $ match line boundaries
re.DOTALL      # . matches newlines
re.VERBOSE     # Allow comments and whitespace in pattern
```

---

## Example Document Formats

### Format A: Simple Numbered List
```
1   Papel bond A4 80 gramos    500   u
2   Tóner HP LaserJet negro    10    Ud
3   Lápices de color variados  24    pz
```

### Format B: Descriptive with Reference
```
REF-001  Papel bond A4 80 gramos    500   u
REF-002  Tóner HP LaserJet negro    10    Ud
REF-003  Lápices de color variados  24    pz
```

### Format C: Labeled Fields
```
Código: REF-001
Descripción: Papel bond A4 80 gramos
Cantidad: 500
Unidad: u

Código: REF-002
Descripción: Tóner HP LaserJet negro
Cantidad: 10
Unidad: Ud
```

### Format D: Table-like
```
1 | Papel bond A4 80 gramos | 500 | u
2 | Tóner HP LaserJet negro | 10 | Ud
3 | Lápices de color variados | 24 | pz
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pattern not matching | Add `re.IGNORECASE` flag or adjust case in pattern |
| Matches too much | Make quantifier non-greedy: `+?` instead of `+` |
| Accented characters not matching | Ensure pattern includes: `áéíóúñüAÉÍÓÚÑÜ` |
| Number format issues | Replace `,` with `.` after extraction |
| Whitespace issues | Use `\s+` instead of single space, then normalize |
| Unit not recognized | Check `UNIT_PATTERNS` - may need to add custom units |
