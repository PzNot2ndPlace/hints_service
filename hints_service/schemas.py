from enum import Enum
from pydantic import BaseModel, validator
from datetime import datetime
from typing import List


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
    trigger_type: TriggerType
    trigger_value: str


class NoteDto(BaseModel):
    text: str
    createdAt: str
    updatedAt: str
    categoryType: CategoryType
    triggers: List[TriggerDto]

    @validator("createdAt", "updatedAt")
    def validate_time(cls, v):
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
    hint_text: str
