"""Обработка превью трансляции (320×180, JPEG, crop cover)."""
from __future__ import annotations

import io

from PIL import Image

THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 180
MAX_THUMBNAIL_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def _crop_center_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    target_ratio = target_w / target_h
    src_ratio = img.width / img.height

    if src_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        return img.crop((left, 0, left + new_w, img.height))

    new_h = int(img.width / target_ratio)
    top = (img.height - new_h) // 2
    return img.crop((0, top, img.width, top + new_h))


def process_custom_thumbnail(image_bytes: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
    except Exception as exc:
        raise ValueError("Не удалось прочитать изображение") from exc

    if img.width < 1 or img.height < 1:
        raise ValueError("Пустое изображение")

    img = _crop_center_cover(img, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)
    img = img.resize((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue()
