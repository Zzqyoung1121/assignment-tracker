import difflib
import easyocr
import cv2
import numpy as np

_reader = None

MAX_SIDE = 1920  # 超过此尺寸先缩小，避免 EasyOCR 在高分辨率图上裁出零尺寸区域


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        # 首次调用会下载模型文件（约 200MB），之后缓存到 ~/.EasyOCR/
        _reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    return _reader


def _load_and_resize(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片：{image_path}")
    h, w = img.shape[:2]
    if max(h, w) > MAX_SIDE:
        scale = MAX_SIDE / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def recognize_names_from_image(image_path: str, student_names: list[str]) -> list[dict]:
    """
    用 EasyOCR 识别图片文字，再与学生名单做模糊匹配。
    返回 [{"name": "张三", "confidence": 0.87}, ...]
    """
    reader = _get_reader()
    img = _load_and_resize(image_path)
    raw = reader.readtext(img)  # 传 numpy array 避免重复读盘
    ocr_texts = [(text.strip(), float(conf)) for (_, text, conf) in raw if text.strip()]

    candidates = []
    matched: set[str] = set()

    for name in student_names:
        if name in matched:
            continue
        best_score = 0.0
        best_conf = 0.0

        for text, conf in ocr_texts:
            if name in text:
                score = 1.0
            elif text in name and len(text) >= 2:
                score = 0.9
            else:
                score = difflib.SequenceMatcher(None, name, text).ratio()

            if score > best_score:
                best_score = score
                best_conf = conf

        if best_score >= 0.6:
            matched.add(name)
            candidates.append({
                "name": name,
                "confidence": round(best_score * best_conf, 2),
            })

    return candidates
