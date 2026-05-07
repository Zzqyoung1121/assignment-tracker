from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=True)

    students = relationship("Student", back_populates="class_")
    homework_tasks = relationship("HomeworkTask", back_populates="class_")
    upload_images = relationship("UploadImage", back_populates="class_")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    name = Column(String(100), nullable=False)
    student_number = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=True)

    class_ = relationship("Class", back_populates="students")
    submissions = relationship("Submission", back_populates="student")


class HomeworkTask(Base):
    __tablename__ = "homework_tasks"

    id = Column(Integer, primary_key=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject = Column(String(100), nullable=False)
    due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)

    class_ = relationship("Class", back_populates="homework_tasks")
    submissions = relationship("Submission", back_populates="task")


class UploadImage(Base):
    __tablename__ = "upload_images"

    id = Column(Integer, primary_key=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(255), nullable=False)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)

    class_ = relationship("Class", back_populates="upload_images")
    submissions = relationship("Submission", back_populates="image")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, nullable=False)
    task_id = Column(Integer, ForeignKey("homework_tasks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    image_id = Column(Integer, ForeignKey("upload_images.id"), nullable=True)
    status = Column(String(20), nullable=False)
    source = Column(String(30), nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    task = relationship("HomeworkTask", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")
    image = relationship("UploadImage", back_populates="submissions")
