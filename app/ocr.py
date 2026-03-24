import re
from datetime import datetime
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import os

def extract_text_from_file(file_path):
    """Extract text from image or PDF file."""
    # Check if file is PDF
    if file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    else:
        return extract_text_from_image(file_path)

def extract_text_from_image(image_path):
    """Extract text from an image using OCR."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error processing image: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF by converting pages to images."""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        
        # Extract text from all pages
        full_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        
        return full_text
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return ""

def extract_amount(text):
    """Extract monetary amount from text."""
    # Look for patterns like €100.50, $100.50, 100.50€, 100,50 EUR, etc.
    patterns = [
        r'[€$£]\s*(\d+[.,]\d{2})',
        r'(\d+[.,]\d{2})\s*[€$£]',
        r'(\d{1,3}(?:[,\.]\d{3})*[.,]\d{2})\s*(?:EUR|USD|GBP|€|\$|£)?',
        r'Total[\s:]*(\d+[.,]\d{2})',
        r'Betrag[\s:]*(\d+[.,]\d{2})',
        r'Amount[\s:]*(\d+[.,]\d{2})',
        r'Summe[\s:]*(\d+[.,]\d{2})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Return the largest amount (likely the total)
            amounts = []
            for match in matches:
                try:
                    # Handle both comma and dot as decimal separator
                    amount_str = match.replace(',', '.')
                    amounts.append(float(amount_str))
                except:
                    continue
            if amounts:
                return max(amounts)
    
    return None

def extract_date(text):
    """Extract date from text."""
    patterns = [
        # DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY
        r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})',
        # YYYY-MM-DD
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match[2]) == 2:
                    year = int(match[2])
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                else:
                    year = int(match[2])
                
                day = int(match[0]) if len(match[0]) > len(match[1]) else int(match[2])
                month = int(match[1])
                
                # Validate date
                dt = datetime(year, month, day)
                # Only return dates within reasonable range
                if 2000 <= year <= 2050:
                    return dt.strftime('%Y-%m-%d')
            except:
                continue
    
    return None

def extract_vendor(text):
    """Extract vendor/merchant name from text."""
    lines = text.split('\n')
    
    # Common patterns to skip
    skip_patterns = [
        'invoice', 'rechnung', 'facture', 'bill', 'quittung', 'kassenbon',
        'tel', 'phone', 'email', 'www', 'http', 'fax', 'ust-id', 'tax id',
        'total', 'summe', 'betrag', 'amount', 'menge', 'quantity',
        'datum', 'date', 'receipt', 'beleg', 'nr', 'no', 'date'
    ]
    
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        # Skip empty lines, very short lines, and lines with numbers only
        if len(line) < 3 or line.isdigit():
            continue
        # Skip lines containing common keywords
        if any(pattern in line.lower() for pattern in skip_patterns):
            continue
        # Return first plausible company name (often at the top)
        if len(line) > 3 and not line.startswith('€') and not line.startswith('$'):
            return line
    
    return None

def process_invoice(file_path):
    """Process an invoice image or PDF and extract relevant information."""
    text = extract_text_from_file(file_path)
    
    if not text.strip():
        return None
    
    return {
        'amount': extract_amount(text),
        'date': extract_date(text),
        'vendor': extract_vendor(text),
        'raw_text': text
    }
