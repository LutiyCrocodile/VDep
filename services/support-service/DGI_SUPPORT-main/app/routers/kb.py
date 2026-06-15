from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.templates import templates
from app.core.deps import get_current_user, require_role
from app.db.models import KbArticle, KbCategory, KbFile, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/kb")

_KB_UPLOAD_DIR = Path("app") / "media" / "kb"
_KB_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_CATEGORY_LABELS = {
    KbCategory.faq: "Частые вопросы",
    KbCategory.guide: "Инструкции",
    KbCategory.policy: "Политики и регламенты",
    KbCategory.software: "ПО и установщики",
    KbCategory.template: "Шаблоны документов",
}


def _can_edit(user: User) -> bool:
    return user.role in (UserRole.engineer, UserRole.admin)


# ── Public: list articles ────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def kb_index(
    request: Request,
    category: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(KbArticle).options(selectinload(KbArticle.author), selectinload(KbArticle.files)).filter(KbArticle.is_published == True)
    if category:
        query = query.filter(KbArticle.category == category)
    result = await db.execute(query.order_by(KbArticle.category, KbArticle.updated_at.desc()))
    articles = result.scalars().all()

    # Standalone files (no article)
    files_result = await db.execute(
        select(KbFile)
        .filter(KbFile.article_id.is_(None))
        .order_by(KbFile.created_at.desc())
    )
    standalone_files = files_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "kb_index.html",
        {
            "user": user,
            "articles": articles,
            "standalone_files": standalone_files,
            "category": category,
            "KbCategory": KbCategory,
            "category_labels": _CATEGORY_LABELS,
            "can_edit": _can_edit(user),
        },
    )


# ── Create article (engineer/admin) ──────────────────────────────────
@router.get("/new", response_class=HTMLResponse)
async def kb_new_form(
    request: Request,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
):
    return templates.TemplateResponse(
        request,
        "kb_edit.html",
        {
            "user": user,
            "article": None,
            "KbCategory": KbCategory,
            "category_labels": _CATEGORY_LABELS,
            "error": None,
        },
    )


@router.post("/new")
async def kb_new_submit(
    title: str = Form(...),
    body: str = Form(""),
    category: str = Form("faq"),
    is_published: str = Form("1"),
    file: UploadFile | None = None,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    article = KbArticle(
        title=title.strip(),
        body=body,
        category=KbCategory(category),
        is_published=is_published == "1",
        author_id=user.id,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    
    # Обработка файла если загружен
    if file and file.filename:
        import os
        from pathlib import Path
        
        media_dir = Path("media/kb")
        media_dir.mkdir(parents=True, exist_ok=True)
        
        file_ext = Path(file.filename).suffix
        safe_name = f"{article.id}_{file.filename}"
        file_path = media_dir / safe_name
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        kb_file = KbFile(
            article_id=article.id,
            uploaded_by_id=user.id,
            file_path=str(file_path),
            original_name=file.filename,
            file_size=len(content),
        )
        db.add(kb_file)
        await db.commit()
    
    return RedirectResponse(url=f"/kb/{article.id}", status_code=303)


# ── Public: view article ─────────────────────────────────────────────
@router.get("/{article_id}", response_class=HTMLResponse)
async def kb_view(
    article_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KbArticle).options(selectinload(KbArticle.author), selectinload(KbArticle.files)).filter(KbArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article or (not article.is_published and not _can_edit(user)):
        return RedirectResponse(url="/kb", status_code=303)

    return templates.TemplateResponse(
        request,
        "kb_view.html",
        {
            "user": user,
            "article": article,
            "KbCategory": KbCategory,
            "category_labels": _CATEGORY_LABELS,
            "can_edit": _can_edit(user),
        },
    )


# ── Edit article (engineer/admin) ────────────────────────────────────
@router.get("/{article_id}/edit", response_class=HTMLResponse)
async def kb_edit_form(
    article_id: int,
    request: Request,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KbArticle).options(selectinload(KbArticle.author), selectinload(KbArticle.files)).filter(KbArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        return RedirectResponse(url="/kb", status_code=303)

    return templates.TemplateResponse(
        request,
        "kb_edit.html",
        {
            "user": user,
            "article": article,
            "KbCategory": KbCategory,
            "category_labels": _CATEGORY_LABELS,
            "error": None,
        },
    )


@router.post("/{article_id}/edit")
async def kb_edit_submit(
    article_id: int,
    title: str = Form(...),
    body: str = Form(""),
    category: str = Form("faq"),
    is_published: str = Form("1"),
    file: UploadFile | None = None,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KbArticle).options(selectinload(KbArticle.author), selectinload(KbArticle.files)).filter(KbArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        return RedirectResponse(url="/kb", status_code=303)

    article.title = title.strip()
    article.body = body
    article.category = KbCategory(category)
    article.is_published = is_published == "1"
    article.updated_at = datetime.utcnow()
    
    # Обработка файла если загружен
    if file and file.filename:
        from pathlib import Path
        
        media_dir = Path("media/kb")
        media_dir.mkdir(parents=True, exist_ok=True)
        
        file_ext = Path(file.filename).suffix
        safe_name = f"{article.id}_{file.filename}"
        file_path = media_dir / safe_name
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        kb_file = KbFile(
            article_id=article.id,
            uploaded_by_id=user.id,
            file_path=str(file_path),
            original_name=file.filename,
            file_size=len(content),
        )
        db.add(kb_file)
    
    await db.commit()
    return RedirectResponse(url=f"/kb/{article.id}", status_code=303)


# ── Delete article (engineer/admin) ──────────────────────────────────
@router.post("/{article_id}/delete")
async def kb_delete(
    article_id: int,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KbArticle).options(selectinload(KbArticle.author), selectinload(KbArticle.files)).filter(KbArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        return RedirectResponse(url="/kb", status_code=303)

    # Delete associated files from disk
    files_result = await db.execute(select(KbFile).filter(KbFile.article_id == article_id))
    files = files_result.scalars().all()
    for f in files:
        fp = Path(f.file_path)
        if fp.exists():
            fp.unlink()

    await db.delete(article)
    await db.commit()
    return RedirectResponse(url="/kb", status_code=303)


# ── Upload file (engineer/admin) ─────────────────────────────────────
@router.post("/upload")
async def kb_upload_file(
    file: UploadFile = File(...),
    article_id: str = Form(""),
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_name = f"{ts}_{file.filename}"
    dest = _KB_UPLOAD_DIR / safe_name

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(dest)

    art_id = int(article_id) if article_id else None

    kb_file = KbFile(
        article_id=art_id,
        uploaded_by_id=user.id,
        file_path=str(dest),
        original_name=file.filename or "file",
        file_size=file_size,
    )
    db.add(kb_file)
    await db.commit()

    if art_id:
        return RedirectResponse(url=f"/kb/{art_id}", status_code=303)
    return RedirectResponse(url="/kb", status_code=303)


# ── Download file ────────────────────────────────────────────────────
@router.get("/files/{file_id}/download")
async def kb_download_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import FileResponse

    result = await db.execute(select(KbFile).filter(KbFile.id == file_id))
    kb_file = result.scalar_one_or_none()
    if not kb_file:
        return RedirectResponse(url="/kb", status_code=303)

    fp = Path(kb_file.file_path)
    if not fp.exists():
        return RedirectResponse(url="/kb", status_code=303)

    return FileResponse(fp, filename=kb_file.original_name, media_type="application/octet-stream")


# ── Delete file (engineer/admin) ─────────────────────────────────────
@router.post("/files/{file_id}/delete")
async def kb_delete_file(
    file_id: int,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KbFile).filter(KbFile.id == file_id))
    kb_file = result.scalar_one_or_none()
    if not kb_file:
        return RedirectResponse(url="/kb", status_code=303)

    fp = Path(kb_file.file_path)
    if fp.exists():
        fp.unlink()

    art_id = kb_file.article_id
    await db.delete(kb_file)
    await db.commit()

    if art_id:
        return RedirectResponse(url=f"/kb/{art_id}", status_code=303)
    return RedirectResponse(url="/kb", status_code=303)
