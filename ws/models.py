from typing import Optional, List
from decimal import Decimal
from enum import IntEnum

from pydantic import BaseModel, Field, model_validator,field_validator, ConfigDict, EmailStr
from datetime import datetime, date

from digital_scales.models import DigitalScaleItem, DigitalScaleUploadRequest