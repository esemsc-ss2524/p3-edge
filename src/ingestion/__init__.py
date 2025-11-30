"""
Data ingestion components for P3-Edge.
"""

from .receipt_ocr import ReceiptOCR, ReceiptItem, process_receipt_image
from .smart_fridge_simulator import SmartFridgeSimulator, get_mock_inventory

__all__ = [
    "ReceiptOCR",
    "ReceiptItem",
    "process_receipt_image",
    "SmartFridgeSimulator",
    "get_mock_inventory",
]
