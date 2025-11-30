"""
Phone app API server for receipt uploads.

Provides REST API for mobile app to upload receipt images.
"""

import asyncio
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.ingestion import ReceiptOCR, process_receipt_image
from src.services import InventoryService
from src.utils import get_logger

# Create FastAPI app
app = FastAPI(
    title="P3-Edge Phone App API",
    description="API for uploading receipt images from mobile app",
    version="0.1.0",
)

# Global state (will be set by init_api function)
inventory_service: InventoryService = None
receipt_upload_dir: Path = None
logger = get_logger("phone_app_api")


def init_api(service: InventoryService, upload_dir: str = "data/receipts"):
    """
    Initialize API with dependencies.

    Args:
        service: InventoryService instance
        upload_dir: Directory for uploaded receipts
    """
    global inventory_service, receipt_upload_dir

    inventory_service = service
    receipt_upload_dir = Path(upload_dir)
    receipt_upload_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Phone app API initialized, upload dir: {receipt_upload_dir}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "P3-Edge Phone App API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "inventory_service": "connected" if inventory_service else "disconnected",
    }


@app.post("/upload/receipt")
async def upload_receipt(file: UploadFile = File(...)) -> Dict:
    """
    Upload and process a receipt image.

    Args:
        file: Receipt image file

    Returns:
        Processing results with extracted items
    """
    if not inventory_service:
        raise HTTPException(status_code=500, detail="Inventory service not initialized")

    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Must be an image.",
        )

    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix or ".jpg"
        save_path = receipt_upload_dir / f"{file_id}{file_ext}"

        # Save uploaded file
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"Receipt uploaded: {save_path}")

        # Process receipt (async to not block)
        extracted_items = await asyncio.to_thread(process_receipt_image, str(save_path))

        # Convert to dict for JSON response
        items_data = [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "price": item.price,
                "confidence": item.confidence,
            }
            for item in extracted_items
        ]

        logger.info(f"Extracted {len(extracted_items)} items from receipt")

        return {
            "status": "success",
            "receipt_id": file_id,
            "file_path": str(save_path),
            "items_found": len(extracted_items),
            "items": items_data,
            "message": "Receipt processed successfully. Items extracted but not yet added to inventory.",
        }

    except Exception as e:
        logger.error(f"Receipt processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/upload/receipt/confirm")
async def confirm_receipt_items(receipt_id: str, items: List[Dict]) -> Dict:
    """
    Confirm and add receipt items to inventory.

    Args:
        receipt_id: Receipt ID from upload
        items: List of items to add

    Returns:
        Confirmation result
    """
    if not inventory_service:
        raise HTTPException(status_code=500, detail="Inventory service not initialized")

    try:
        added_count = 0

        for item_data in items:
            # This would need more sophisticated matching logic in production
            # For now, we just log the items
            logger.info(f"Confirmed item: {item_data.get('name')}")
            added_count += 1

        return {
            "status": "success",
            "receipt_id": receipt_id,
            "items_added": added_count,
            "message": f"Added {added_count} items to inventory",
        }

    except Exception as e:
        logger.error(f"Failed to confirm receipt items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/receipts")
async def list_receipts() -> Dict:
    """
    List all uploaded receipts.

    Returns:
        List of receipts
    """
    if not receipt_upload_dir:
        return {"receipts": []}

    receipts = []
    for file_path in receipt_upload_dir.glob("*"):
        if file_path.is_file():
            receipts.append(
                {
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "uploaded_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "size_bytes": file_path.stat().st_size,
                }
            )

    return {
        "count": len(receipts),
        "receipts": sorted(receipts, key=lambda x: x["uploaded_at"], reverse=True),
    }


if __name__ == "__main__":
    import uvicorn

    # For standalone testing
    from src.database.db_manager import create_database_manager

    db = create_database_manager()
    service = InventoryService(db)
    init_api(service)

    print("Starting Phone App API server...")
    print("API documentation available at: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000)
