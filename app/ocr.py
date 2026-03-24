import pytesseract
from PIL import Image
import re
from datetime import datetime

def extract_text_from_image(image_path):
    """Extract text from image using OCR"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"Error processing image: {str(e)}"

def extract_amount(text):
    """Extract monetary amount from text"""
    # Look for patterns like $123.45, 123.45 EUR, Total: 123.45, etc.
    patterns = [
        r'[Tt]otal[:\s]*[$\u20ac\u00a3]?\s*([\d,]+\.?\d{0,2})',
        r'[Aa]mount[:\s]*[$\u20ac\u00a3]?\s*([\d,]+\.?\d{0,2})',
        r'[$\u20ac\u00a3]\s*([\d,]+\.\d{2})',
        r'([\d,]+\.\d{2})\s*(?:USD|EUR|GBP|$|\u20ac|\u00a3)',
        r'\b([\d,]+\.\d{2})\b'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Get the largest amount (likely the total)
            amounts = [float(m.replace(',', '')) for m in matches]
            return max(amounts)
    
    return None

def extract_date(text):
    """Extract date from text"""
    # Various date patterns
    patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',    # YYYY-MM-DD
        r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',      # DD.MM.YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                groups = match.groups()
                if len(groups[2]) == 2:
                    year = int(groups[2]) + 2000 if int(groups[2]) < 50 else int(groups[2]) + 1900
                else:
                    year = int(groups[2])
                
                # Try MM/DD/YYYY first (US format)
                try:
                    return datetime(year, int(groups[0]), int(groups[1])).date()
                except ValueError:
                    # Try DD/MM/YYYY (European format)
                    return datetime(year, int(groups[1]), int(groups[0])).date()
            except:
                continue
    
    return None

def extract_vendor(text):
    """Extract vendor/merchant name from text"""
    lines = text.strip().split('\n')
    
    # First non-empty line is often the vendor name
    for line in lines:
        line = line.strip()
        if line and len(line) > 2 and not line.lower().startswith(('date', 'total', 'amount', 'invoice', 'receipt')):
            return line[:200]  # Limit length
    
    return None

def process_invoice(image_path):
    """Process invoice image and extract data"""
    text = extract_text_from_image(image_path)
    
    return {
        'raw_text': text,
        'amount': extract_amount(text),
        'date': extract_date(text),
        'vendor': extract_vendor(text)
    }
