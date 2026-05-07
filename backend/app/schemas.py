from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional

# Class
class ClassCreate(BaseModel):
    name: str

class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: Optional[datetime] = None

# Student
class StudentCreate(BaseModel):
    name: str
    student_number: Optional[str] = None

class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_id: int
    name: str
    student_number: Optional[str] = None

# HomeworkTask
class HomeworkTaskCreate(BaseModel):
    class_id: int
    subject: str
    due_date: Optional[date] = None
    notes: Optional[str] = None

class HomeworkTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_id: int
    subject: str
    due_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

# UploadImage
class UploadImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    ocr_text: Optional[str] = None

# OCR
class OcrRecognizeRequest(BaseModel):
    task_id: int
    image_ids: list[int]

class OcrCandidate(BaseModel):
    name: str
    confidence: float

class OcrRecognizeResponse(BaseModel):
    image_id: int
    candidates: list[OcrCandidate]

# Submission
class SubmissionConfirm(BaseModel):
    task_id: int
    student_id: int
    status: str  # submitted | missing | pending
    image_id: Optional[int] = None

# Report
class HomeworkReportEntry(BaseModel):
    student_id: int
    name: str
    status: str
    image_id: Optional[int] = None

class HomeworkReport(BaseModel):
    task_id: int
    total: int
    submitted_count: int
    missing_count: int
    entries: list[HomeworkReportEntry]
