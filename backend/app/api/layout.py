from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document
from app.models.layout_region import LayoutRegion
from app.schemas.layout import LayoutRegionResponse


router = APIRouter(prefix="/documents", tags=["Document Layout Detection"])


@router.get("/{document_id}/layout", response_model=List[LayoutRegionResponse])
async def get_layout_regions(document_id: str, db: Session = Depends(get_db)):
    if not db.get(Document, document_id):
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")
    return (
        db.query(LayoutRegion)
        .filter(LayoutRegion.document_id == document_id)
        .order_by(LayoutRegion.id)
        .all()
    )
