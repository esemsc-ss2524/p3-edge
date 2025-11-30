# Sample Receipt Test Data

This directory contains sample receipt text files for testing the OCR functionality.

## How to Use

1. **Open any receipt .txt file** in a text editor or viewer
2. **Take a screenshot** of the receipt text (make sure the text is clearly visible)
3. **Upload the screenshot** using the "📷 Upload Receipt" button in the P3-Edge inventory page
4. **Review the extracted items** and verify OCR accuracy

## Included Receipts

### walmart_receipt.txt
- **Items**: 12 grocery items
- **Total**: $63.18
- **Format**: Standard Walmart receipt with item names and prices
- **Best for**: Testing basic OCR with common formatting

### target_receipt.txt
- **Items**: 10 grocery items
- **Total**: $67.61
- **Format**: Target receipt with "@ price" notation
- **Best for**: Testing quantity extraction

### whole_foods_receipt.txt
- **Items**: 14 organic/specialty items
- **Total**: $105.31
- **Format**: Whole Foods receipt with longer item names
- **Best for**: Testing with premium/organic product names

### kroger_receipt.txt
- **Items**: 11 items (includes multiples)
- **Total**: $50.92
- **Format**: Kroger receipt with "@ price" and quantity
- **Best for**: Testing quantity detection (e.g., "2 @ $3.99")

## Tips for Best Results

1. **Good Lighting**: Screenshot in good lighting or use a high-contrast theme
2. **Clear Text**: Ensure text is sharp and readable
3. **No Cropping**: Include the full receipt for better context
4. **Standard Fonts**: These samples use monospace fonts which OCR handles well

## Expected Extraction

The OCR pipeline should extract:
- **Item names**: ORGANIC MILK GALLON → "Organic Milk Gallon"
- **Prices**: $5.99 → 5.99
- **Quantities**: 2 @ $3.99 → quantity: 2
- **Confidence scores**: Most items should have 80%+ confidence

## Testing the API

You can also test the phone app API:

```bash
# Start the API server
python src/api/phone_app.py

# Upload via API (requires actual image file)
curl -X POST "http://localhost:8000/upload/receipt" \
  -F "file=@path/to/screenshot.png"
```

## Note

These are text-based receipts. For best OCR results:
1. Take a clean screenshot with good resolution
2. Use a white background and black text
3. Ensure the font size is readable (14pt or larger recommended)
4. Save as PNG or JPEG with good quality
