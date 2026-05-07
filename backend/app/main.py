import csv
import io
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .db import engine, get_db, Base
from .models import Class, Student, HomeworkTask, UploadImage, Submission
from .schemas import (
    ClassCreate, ClassOut,
    StudentCreate, StudentOut,
    HomeworkTaskCreate, HomeworkTaskOut,
    UploadImageOut,
    OcrRecognizeRequest, OcrRecognizeResponse, OcrCandidate,
    SubmissionConfirm,
    HomeworkReport, HomeworkReportEntry,
)
from .ocr_client import recognize_names_from_image

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="作业追踪系统")

IMAGES_DIR = Path("data/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/index.html")


# ── Classes ──────────────────────────────────────────────────────────────────

@app.post("/classes", response_model=ClassOut)
def create_class(body: ClassCreate, db: Session = Depends(get_db)):
    obj = Class(name=body.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/classes", response_model=List[ClassOut])
def list_classes(db: Session = Depends(get_db)):
    return db.query(Class).all()


# ── Students ──────────────────────────────────────────────────────────────────

@app.get("/classes/{class_id}/students", response_model=List[StudentOut])
def list_students(class_id: int, db: Session = Depends(get_db)):
    return db.query(Student).filter(Student.class_id == class_id).all()


@app.post("/classes/{class_id}/students", response_model=StudentOut)
def add_student(class_id: int, body: StudentCreate, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    obj = Student(class_id=class_id, name=body.name, student_number=body.student_number)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.post("/students/import")
async def import_students(class_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    CSV/TSV 文件，第一行为表头（跳过）。
    格式：第一列学号，第二列姓名。
    支持 UTF-8、UTF-8 BOM、GBK 编码。
    """
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    raw = await file.read()
    text = None
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="文件编码不支持，请用 UTF-8 或 GBK 保存")

    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",\t")
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(io.StringIO(text), dialect))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="文件无数据行（至少需要表头 + 一行数据）")

    added, skipped = [], []
    for i, row in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in row):
            continue
        if len(row) < 2:
            skipped.append(f"第{i}行列数不足，已跳过")
            continue
        student_number = row[0].strip()
        name = row[1].strip()
        if not name:
            skipped.append(f"第{i}行姓名为空，已跳过")
            continue
        db.add(Student(class_id=class_id, name=name, student_number=student_number or None))
        added.append({"student_number": student_number, "name": name})

    db.commit()
    return {"added": len(added), "students": added, "skipped": skipped}


# ── HomeworkTask ──────────────────────────────────────────────────────────────

@app.post("/homework_tasks", response_model=HomeworkTaskOut)
def create_task(body: HomeworkTaskCreate, db: Session = Depends(get_db)):
    obj = HomeworkTask(
        class_id=body.class_id,
        subject=body.subject,
        due_date=body.due_date,
        notes=body.notes,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/classes/{class_id}/homework_tasks", response_model=List[HomeworkTaskOut])
def list_tasks(class_id: int, db: Session = Depends(get_db)):
    return db.query(HomeworkTask).filter(HomeworkTask.class_id == class_id).all()


# ── Images ────────────────────────────────────────────────────────────────────

@app.post("/images/upload", response_model=List[UploadImageOut])
async def upload_images(
    class_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    results = []
    for f in files:
        ext = Path(f.filename).suffix if f.filename else ".jpg"
        unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        save_path = IMAGES_DIR / unique_name
        content = await f.read()
        save_path.write_bytes(content)
        img = UploadImage(
            class_id=class_id,
            filename=f.filename or unique_name,
            storage_path=str(save_path),
        )
        db.add(img)
        db.commit()
        db.refresh(img)
        results.append(img)
    return results


# ── OCR ───────────────────────────────────────────────────────────────────────

@app.post("/ocr/recognize", response_model=List[OcrRecognizeResponse])
def ocr_recognize(body: OcrRecognizeRequest, db: Session = Depends(get_db)):
    task = db.query(HomeworkTask).filter(HomeworkTask.id == body.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="作业任务不存在")
    students = db.query(Student).filter(Student.class_id == task.class_id).all()
    student_names = [s.name for s in students]
    student_map = {s.name: s.id for s in students}

    responses = []
    for image_id in body.image_ids:
        img = db.query(UploadImage).filter(UploadImage.id == image_id).first()
        if not img:
            continue
        try:
            candidates_raw = recognize_names_from_image(img.storage_path, student_names)
        except Exception as e:
            candidates_raw = []
        candidates = [OcrCandidate(name=c["name"], confidence=c.get("confidence", 0.9))
                      for c in candidates_raw if "name" in c]
        # 写回 ocr_text
        img.ocr_text = str([c.name for c in candidates])
        db.commit()
        # 自动创建 submissions
        for c in candidates:
            sid = student_map.get(c.name)
            if sid:
                existing = db.query(Submission).filter(
                    Submission.task_id == body.task_id,
                    Submission.student_id == sid,
                ).first()
                if not existing:
                    sub = Submission(
                        task_id=body.task_id,
                        student_id=sid,
                        image_id=image_id,
                        status="submitted",
                        source="ocr",
                    )
                    db.add(sub)
        db.commit()
        responses.append(OcrRecognizeResponse(image_id=image_id, candidates=candidates))
    return responses


# ── Submissions ───────────────────────────────────────────────────────────────

@app.post("/submissions/confirm", response_model=dict)
def confirm_submission(body: SubmissionConfirm, db: Session = Depends(get_db)):
    existing = db.query(Submission).filter(
        Submission.task_id == body.task_id,
        Submission.student_id == body.student_id,
    ).first()
    if existing:
        existing.status = body.status
        existing.image_id = body.image_id
        existing.updated_at = datetime.utcnow()
    else:
        sub = Submission(
            task_id=body.task_id,
            student_id=body.student_id,
            image_id=body.image_id,
            status=body.status,
            source="manual",
        )
        db.add(sub)
    db.commit()
    return {"ok": True}


# ── Reports ───────────────────────────────────────────────────────────────────

@app.get("/reports/homework/{task_id}", response_model=HomeworkReport)
def homework_report(task_id: int, db: Session = Depends(get_db)):
    task = db.query(HomeworkTask).filter(HomeworkTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="作业任务不存在")
    students = db.query(Student).filter(Student.class_id == task.class_id).all()
    submissions = db.query(Submission).filter(Submission.task_id == task_id).all()
    sub_map = {s.student_id: s for s in submissions}
    entries = []
    submitted_count = 0
    for stu in students:
        sub = sub_map.get(stu.id)
        status = sub.status if sub else "missing"
        image_id = sub.image_id if sub else None
        if status == "submitted":
            submitted_count += 1
        entries.append(HomeworkReportEntry(
            student_id=stu.id,
            name=stu.name,
            status=status,
            image_id=image_id,
        ))
    return HomeworkReport(
        task_id=task_id,
        total=len(students),
        submitted_count=submitted_count,
        missing_count=len(students) - submitted_count,
        entries=entries,
    )


# ── Report Download ───────────────────────────────────────────────────────────

@app.get("/reports/homework/{task_id}/download")
def download_report(task_id: int, db: Session = Depends(get_db)):
    task = db.query(HomeworkTask).filter(HomeworkTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="作业任务不存在")
    cls = db.query(Class).filter(Class.id == task.class_id).first()
    students = db.query(Student).filter(Student.class_id == task.class_id).all()
    submissions = db.query(Submission).filter(Submission.task_id == task_id).all()
    sub_map = {s.student_id: s for s in submissions}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["学号", "姓名", "状态", "来源"])
    status_zh = {"submitted": "已交", "missing": "未交", "pending": "待确认"}
    for stu in students:
        sub = sub_map.get(stu.id)
        status = sub.status if sub else "missing"
        source = sub.source if sub else ""
        writer.writerow([stu.student_number or "", stu.name, status_zh.get(status, status), source])

    content = buf.getvalue().encode("utf-8-sig")
    filename = f"{cls.name}_{task.subject}.csv" if cls else f"task_{task_id}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# ── Clear Submissions ──────────────────────────────────────────────────────────

@app.delete("/submissions/task/{task_id}")
def clear_task_submissions(task_id: int, db: Session = Depends(get_db)):
    task = db.query(HomeworkTask).filter(HomeworkTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="作业任务不存在")
    count = db.query(Submission).filter(Submission.task_id == task_id).delete()
    db.commit()
    return {"deleted": count}


# ── Static UI ─────────────────────────────────────────────────────────────────

ui_path = Path("ui")
if ui_path.exists():
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")
