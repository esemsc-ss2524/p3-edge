"""
Receipt OCR pipeline for extracting grocery items from receipt images.

Uses Tesseract OCR with preprocessing for better accuracy.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image

from src.utils import get_logger


@dataclass
class ReceiptItem:
    """Extracted item from receipt."""

    name: str
    quantity: float = 1.0
    unit: Optional[str] = None
    price: Optional[float] = None
    confidence: float = 0.0


class ReceiptOCR:
    """OCR pipeline for receipt processing."""

    def __init__(self):
        """Initialize OCR pipeline."""
        self.logger = get_logger("receipt_ocr")

        # Common grocery item patterns
        self.item_patterns = [
            # Pattern: ITEM NAME ... $PRICE
            r"^([\w\s\-']+?)\s+[\.\s]+\s+\$?(\d+\.\d{2})$",
            # Pattern: ITEM NAME $PRICE
            r"^([\w\s\-']+?)\s+\$?(\d+\.\d{2})$",
            # Pattern: QTY ITEM NAME @ PRICE
            r"^(\d+)\s+([\w\s\-']+?)\s+@\s+\$?(\d+\.\d{2})$",
        ]

        # Quantity patterns
        self.quantity_pattern = r"(\d+(?:\.\d+)?)\s*(lb|oz|kg|g|ct|count|gallon|liter)?s?"

    def process_receipt(self, image_path: str) -> List[ReceiptItem]:
        """
        Process receipt image and extract items.

        Args:
            image_path: Path to receipt image

        Returns:
            List of extracted ReceiptItems
        """
        self.logger.info(f"Processing receipt: {image_path}")

        try:
            # Load and preprocess image
            processed_image = self._preprocess_image(image_path)

            # Perform OCR
            text = self._extract_text(processed_image)

            # Parse items from text
            items = self._parse_items(text)

            self.logger.info(f"Extracted {len(items)} items from receipt")
            return items

        except Exception as e:
            self.logger.error(f"Failed to process receipt: {e}")
            raise

    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.

        Args:
            image_path: Path to image

        Returns:
            Preprocessed image as numpy array
        """
        # Read image
        img = cv2.imread(image_path)

        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Resize for better OCR (target height ~1200px)
        height, width = gray.shape
        if height < 1200:
            scale = 1200 / height
            new_width = int(width * scale)
            gray = cv2.resize(gray, (new_width, 1200), interpolation=cv2.INTER_CUBIC)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        # Deskew if needed
        deskewed = self._deskew(binary)

        # Enhance contrast
        enhanced = cv2.equalizeHist(deskewed)

        return enhanced

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Deskew image by detecting and rotating text.

        Args:
            image: Input image

        Returns:
            Deskewed image
        """
        # Detect edges
        edges = cv2.Canny(image, 50, 150, apertureSize=3)

        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

        if lines is None:
            return image

        # Calculate rotation angle
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = theta * 180 / np.pi
            if 85 <= angle <= 95:  # Near vertical lines
                angles.append(angle - 90)

        if not angles:
            return image

        # Get median angle
        median_angle = np.median(angles)

        # Rotate image if angle is significant
        if abs(median_angle) > 0.5:
            height, width = image.shape
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                image,
                rotation_matrix,
                (width, height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated

        return image

    def _extract_text(self, image: np.ndarray) -> str:
        """
        Extract text from preprocessed image using Tesseract.

        Args:
            image: Preprocessed image

        Returns:
            Extracted text
        """
        # Convert to PIL Image
        pil_image = Image.fromarray(image)

        # Tesseract config for receipts
        # Allow common receipt characters without problematic quotes
        custom_config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,$@- "

        # Perform OCR
        text = pytesseract.image_to_string(pil_image, config=custom_config)

        return text

    def _parse_items(self, text: str) -> List[ReceiptItem]:
        """
        Parse grocery items from OCR text.

        Args:
            text: OCR extracted text

        Returns:
            List of ReceiptItems
        """
        items = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and headers/footers
            if not line or len(line) < 3:
                continue

            # Skip common receipt header/footer patterns
            if self._is_header_footer(line):
                continue

            # Try to extract item
            item = self._extract_item(line)
            if item:
                items.append(item)

        return items

    def _is_header_footer(self, line: str) -> bool:
        """Check if line is likely a header or footer."""
        lower_line = line.lower()

        # Common header/footer keywords
        keywords = [
            "store",
            "walmart",
            "target",
            "kroger",
            "safeway",
            "total",
            "subtotal",
            "tax",
            "change",
            "cash",
            "credit",
            "card",
            "thank you",
            "receipt",
            "date",
            "time",
            "cashier",
        ]

        return any(keyword in lower_line for keyword in keywords)

    def _extract_item(self, line: str) -> Optional[ReceiptItem]:
        """
        Extract item from a single line.

        Args:
            line: Text line

        Returns:
            ReceiptItem or None if extraction failed
        """
        # Try each pattern
        for pattern in self.item_patterns:
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groups()

                if len(groups) == 2:  # name, price
                    name, price = groups
                    return ReceiptItem(
                        name=name.strip(),
                        price=float(price),
                        confidence=0.8,
                    )
                elif len(groups) == 3:  # qty, name, price
                    qty, name, price = groups
                    return ReceiptItem(
                        name=name.strip(),
                        quantity=float(qty),
                        price=float(price),
                        confidence=0.9,
                    )

        # Fallback: just extract name if no price found
        # Remove obvious noise
        cleaned = re.sub(r"[\$\*\#\@]", "", line).strip()
        if len(cleaned) > 3 and cleaned.isalnum() or " " in cleaned:
            return ReceiptItem(name=cleaned, confidence=0.5)

        return None

    def extract_quantity_unit(self, item_name: str) -> Tuple[float, Optional[str], str]:
        """
        Extract quantity and unit from item name.

        Args:
            item_name: Item name possibly containing quantity/unit

        Returns:
            Tuple of (quantity, unit, cleaned_name)
        """
        match = re.search(self.quantity_pattern, item_name, re.IGNORECASE)

        if match:
            qty = float(match.group(1))
            unit = match.group(2).lower() if match.group(2) else None

            # Remove quantity/unit from name
            cleaned_name = item_name[: match.start()].strip()
            if not cleaned_name:
                cleaned_name = item_name[match.end() :].strip()

            return qty, unit, cleaned_name

        return 1.0, None, item_name


def process_receipt_image(image_path: str) -> List[ReceiptItem]:
    """
    Convenience function to process a receipt image.

    Args:
        image_path: Path to receipt image

    Returns:
        List of extracted ReceiptItems
    """
    ocr = ReceiptOCR()
    return ocr.process_receipt(image_path)
