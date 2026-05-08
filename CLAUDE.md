# backend-service — CLAUDE.md

## 项目概述
老师作业收取追踪系统。老师用手机拍学生作业/试卷，EasyOCR 识别姓名，与班级名单比对，生成已交/未交报告。

## 目录结构
```
D:\backend-service\
├── backend/           # 主服务（FastAPI + SQLite）
│   ├── app/
│   │   ├── main.py        # FastAPI 应用，所有路由
│   │   ├── models.py      # SQLAlchemy ORM（5张表）
│   │   ├── schemas.py     # Pydantic v2 schemas
│   │   ├── db.py          # 数据库引擎 + get_db()
│   │   └── ocr_client.py  # EasyOCR 识别 + difflib 模糊匹配
│   ├── ui/
│   │   └── index.html     # 移动端单页应用（4 Tab）
│   ├── data/
│   │   ├── app.db         # SQLite 数据库（勿删）
│   │   └── images/        # 上传的作业/试卷图片
│   ├── .venv/             # Python 虚拟环境
│   ├── .env.example       # 环境变量模板（当前无必填项）
│   ├── requirements.txt
│   └── start.bat          # Windows 一键启动
└── ocr_service/           # 预留目录，暂未使用
```

## 启动方式
```bat
cd D:\backend-service\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```
或直接双击 `start.bat`。

**无需 API key**，OCR 使用本地 EasyOCR（首次运行自动下载 ~200MB 模型到 `~/.EasyOCR/`）。

## API 路由清单

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /classes | 列出所有班级 |
| POST | /classes | 创建班级 |
| GET | /classes/{id}/students | 获取班级学生 |
| POST | /classes/{id}/students | 添加单个学生 |
| POST | /students/import | 批量导入（multipart: class_id + file [CSV/TSV]） |
| POST | /homework_tasks | 创建作业任务 |
| GET | /classes/{id}/homework_tasks | 列出作业任务 |
| POST | /images/upload | 上传图片（multipart, query: class_id） |
| POST | /ocr/recognize | OCR 识别并自动生成 submissions |
| POST | /submissions/confirm | 手动改状态 |
| DELETE | /submissions/task/{task_id} | 清除指定任务的全部提交记录 |
| GET | /reports/homework/{task_id} | 获取作业报告 |
| GET | /reports/homework/{task_id}/download | 下载报告 CSV（UTF-8 BOM，Excel 可直接打开） |
| GET | /ui/* | 前端静态文件 |

## 数据库（SQLite: data/app.db）

5张表：`classes` / `students` / `homework_tasks` / `upload_images` / `submissions`

- `submissions.status`：submitted | missing | pending
- `submissions.source`：ocr | manual

## 技术栈
- Python 3.x + FastAPI 0.111 + SQLAlchemy 2 + Pydantic v2
- EasyOCR（ch_sim + en，本地推理，无 GPU）
- SQLite（单文件，数据在 data/app.db）

## 红线
- 不要动 data/app.db 表结构（现有数据）
- 不要提交 .env 文件
- uvicorn 必须用 `python -m uvicorn` 启动，直接调 uvicorn.exe 在此环境会立即退出
