# 作业追踪系统

老师用手机拍学生作业本/试卷，系统自动识别姓名，与班级名单比对，生成交作业情况报告。

## 系统要求

- Windows 10/11
- Python 3.9+（已含 .venv，无需另装）
- 局域网 WiFi（手机与电脑同网段）

## 快速启动

双击 `backend\start.bat`，或在终端运行：

```bat
cd D:\backend-service\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

启动后浏览器自动打开本机页面，并显示手机可访问的局域网 IP：
- 本机：http://localhost:8001/
- 手机：http://（start.bat 启动时显示的 IP）:8001/

> 首次使用 OCR 功能时，程序会自动下载约 200MB 的语言模型，之后缓存到本地，无需再次下载。无需任何 API key。

## 使用流程

1. **班级管理** — 创建班级，上传 CSV 文件（第一列学号、第二列姓名）批量导入学生
2. **作业任务** — 选班级，新建一次收作业任务（填任务名称、截止日期）
3. **拍照上传** — 选任务，拍摄作业/试卷，上传后自动 OCR 识别
4. **查看报告** — 绿色已交、红色未交，可手动切换状态；支持导出 CSV 或清除本次记录重新识别

## 项目结构

```
backend/
├── app/           # 后端源码（FastAPI）
├── ui/            # 前端（单文件 HTML）
├── data/          # 数据库 + 上传图片（重要，勿删）
├── start.bat      # 一键启动
└── requirements.txt
```

## 测试

详见 [backend/TESTING.md](backend/TESTING.md)，包含逐步 PowerShell 命令，覆盖完整业务流程（建班级 → 导学生 → 建任务 → 上传图片 → OCR → 查报告 → 手动改状态）。

## 依赖

fastapi · uvicorn · sqlalchemy · pydantic · easyocr · python-multipart · python-dotenv

**特别感谢 Anthropic 公司的 Claude Sonnet 4.6模型的技术支持**
