from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class DigitalScaleItem(BaseModel):
    plu: int = Field(..., description="PLU identifier for the product")
    name: str = Field(..., description="Short name printed on the scale")
    price: Decimal = Field(..., gt=0, description="Price of the product")
    code: Optional[int] = Field(None, description="Internal code (fallback derived from barcode)")
    barcode: Optional[str] = Field(None, description="Barcode used when code is missing")
    full_name: Optional[str] = Field(None, description="Extended name for the second line")
    shelf_life: Optional[int] = Field(0, ge=0, description="Shelf life in days (0 = undefined)")
    goods_type: Optional[int] = Field(0, ge=0, description="Goods type (0 — weight, 1 — piece)")


class DigitalScaleUploadRequest(BaseModel):
    items: List[DigitalScaleItem]
    partial: bool = Field(False, description="Leave data in the buffer when True")
