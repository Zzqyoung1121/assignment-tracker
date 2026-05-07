# 手动测试指南

所有命令在 PowerShell 中运行，服务需先启动（`start.bat` 或 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8001`）。

---

## 1. 环境验证（启动前）

```powershell
# 确认依赖正常
& ".venv\Scripts\python.exe" -c "import fastapi, easyocr, sqlalchemy, pydantic; print('OK')"
# 期望输出：OK
```

---

## 2. 基础连通性

```powershell
# 服务是否在线
Invoke-RestMethod http://localhost:8001/classes
# 期望：JSON 数组（空数组 [] 或已有数据均正常）
```

---

## 3. 完整业务流程（按顺序执行）

### 第一步：创建班级

```powershell
$class = Invoke-RestMethod -Uri http://localhost:8001/classes `
  -Method POST -ContentType "application/json" `
  -Body '{"name": "三年级1班"}'

$classId = $class.id
Write-Host "班级 ID：$classId"
```

### 第二步：导入学生名单（CSV 文件上传）

```powershell
# 创建临时 CSV（第一列学号，第二列姓名；第一行为表头）
$csv = "学号,姓名`n001,张三`n002,李四`n003,王五`n004,赵六"
$csvPath = "$env:TEMP\test_students.csv"
[System.IO.File]::WriteAllText($csvPath, $csv, [System.Text.Encoding]::UTF8)

$form = @{ file = Get-Item $csvPath }
Invoke-RestMethod -Uri "http://localhost:8001/students/import?class_id=$classId" `
  -Method POST -Form $form
# 期望：{"added": 4, "students": [...], "skipped": []}
```

### 第三步：确认学生列表

```powershell
Invoke-RestMethod "http://localhost:8001/classes/$classId/students"
# 期望：4 条学生记录
```

### 第四步：创建作业任务

```powershell
$task = Invoke-RestMethod -Uri http://localhost:8001/homework_tasks `
  -Method POST -ContentType "application/json" `
  -Body "{`"class_id`": $classId, `"subject`": `"数学`", `"due_date`": `"2026-05-10`"}"

$taskId = $task.id
Write-Host "任务 ID：$taskId"
```

### 第五步：上传图片

```powershell
# 准备一张测试图片（含学生姓名的作业/试卷照片）
# 替换下方路径为实际图片路径
$imgPath = "C:\path\to\test-image.jpg"

$form = @{ files = Get-Item $imgPath }
$imgs = Invoke-RestMethod -Uri "http://localhost:8001/images/upload?class_id=$classId" `
  -Method POST -Form $form

$imageId = $imgs[0].id
Write-Host "图片 ID：$imageId"
```

### 第六步：OCR 识别

```powershell
# 首次运行会下载 EasyOCR 模型（约 200MB），请耐心等待
$ocrResult = Invoke-RestMethod -Uri http://localhost:8001/ocr/recognize `
  -Method POST -ContentType "application/json" `
  -Body "{`"task_id`": $taskId, `"image_ids`": [$imageId]}"

$ocrResult | ConvertTo-Json -Depth 5
# 期望：[{"image_id": N, "candidates": [{"name": "张三", "confidence": 0.87}]}]
```

### 第七步：查看报告

```powershell
$report = Invoke-RestMethod "http://localhost:8001/reports/homework/$taskId"
Write-Host "总人数：$($report.total)，已交：$($report.submitted_count)，未交：$($report.missing_count)"
$report.entries | ForEach-Object { Write-Host "$($_.name): $($_.status)" }
```

### 第八步：手动修改状态

```powershell
# 将某学生改为"已交"
$studentId = (Invoke-RestMethod "http://localhost:8001/classes/$classId/students")[0].id

Invoke-RestMethod -Uri http://localhost:8001/submissions/confirm `
  -Method POST -ContentType "application/json" `
  -Body "{`"task_id`": $taskId, `"student_id`": $studentId, `"status`": `"submitted`"}"
# 期望：{"ok": true}

# 再次查看报告，确认状态已更新
Invoke-RestMethod "http://localhost:8001/reports/homework/$taskId" | Select-Object submitted_count, missing_count
```

### 第九步：下载报告 CSV

```powershell
Invoke-WebRequest -Uri "http://localhost:8001/reports/homework/$taskId/download" `
  -OutFile ".\report_test.csv"
Get-Content ".\report_test.csv"
# 期望：UTF-8 BOM CSV，含表头"学号,姓名,状态,来源"，Excel 可直接打开无乱码
```

### 第十步：清除提交记录并确认

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/submissions/task/$taskId" -Method DELETE
# 期望：{"deleted": N}

$report = Invoke-RestMethod "http://localhost:8001/reports/homework/$taskId"
Write-Host "清除后已交：$($report.submitted_count)"
# 期望：0
```

---

## 4. 手机访问测试

1. 确认手机和电脑在同一 WiFi
2. 获取电脑 IP：`ipconfig | findstr IPv4`
3. 手机浏览器访问 `http://<电脑IP>:8001/`
4. 验证页面正常加载，Tab 切换正常，拍照按钮可调起摄像头

---

## 5. 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| OCR 识别不到姓名 | 图片模糊或姓名写法与名单差异过大 | 在"查看报告"里手动切换状态 |
| 首次 OCR 很慢 | 正在下载 EasyOCR 模型 | 等待完成，之后正常 |
| 手机无法访问 | 防火墙拦截 8001 端口 | 关闭防火墙或添加入站规则允许 8001 |
| uvicorn 启动失败 | 直接运行 uvicorn.exe | 改用 `python -m uvicorn` |
