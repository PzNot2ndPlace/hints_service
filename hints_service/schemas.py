from enum import Enum
from pydantic import BaseModel, validator
from datetime import datetime
from typing import List, Optional


class CategoryType(str, Enum):
    TIME = "Time"
    LOCATION = "Location"
    EVENT = "Event"
    SHOPPING = "Shopping"
    CALL = "Call"
    MEETING = "Meeting"
    DEADLINE = "Deadline"
    HEALTH = "Health"
    ROUTINE = "Routine"
    OTHER = "Other"


class TriggerType(str, Enum):
    TIME = "Time"
    LOCATION = "Location"


class TriggerDto(BaseModel):
    triggerType: TriggerType
    triggerValue: str


class NoteDto(BaseModel):
    text: str
    createdAt: str
    updatedAt: Optional[str] = None  # Поле может быть null
    categoryType: CategoryType
    triggers: List[TriggerDto]

    @validator("createdAt")
    def validate_created_at(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M")
            return v
        except ValueError:
            raise ValueError("Некорректный формат времени. Используйте 'YYYY-MM-DD HH:MM'")

    @validator("updatedAt")
    def validate_updated_at(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M")
            return v
        except ValueError:
            raise ValueError("Некорректный формат времени. Используйте 'YYYY-MM-DD HH:MM'")


class TextBasedHintRequest(BaseModel):
    context: List[NoteDto]
    current_time: str

    @validator("current_time")
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M")
            return v
        except ValueError:
            raise ValueError("Некорректный формат времени. Используйте 'YYYY-MM-DD HH:MM'")


class TextBasedHintResponse(BaseModel):
    note: NoteDto
    hintText: str
