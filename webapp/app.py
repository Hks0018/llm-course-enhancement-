"""Thin web wrapper around course_enhancer.pipeline.run() — upload a course
file, run the (stdlib-only, deterministic) enhancement pipeline, and
download the generated output tree as a zip.

Auth is a single shared password (APP_PASSWORD env var), backed by a signed
cookie so the password itself is only sent once at login.
"""
from __future__ import annotations

import os
import secrets
import shutil
import tempfile
import time
import uuid

from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.concurrency import run_in_threadpool

from course_enhancer import pipeline

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

RUNS_ROOT = os.path.join(tempfile.gettempdir(), "course_enhancer_runs")
RUN_TTL_SECONDS = 2 * 3600  # best-effort cleanup of old runs

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="course-enhancer-session")

app = FastAPI(title="Course Enhancer")


def _cleanup_old_runs() -> None:
    if not os.path.isdir(RUNS_ROOT):
        return
    cutoff = time.time() - RUN_TTL_SECONDS
    for name in os.listdir(RUNS_ROOT):
        path = os.path.join(RUNS_ROOT, name)
        try:
            if os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def require_auth(request: Request) -> None:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Session expired")


@app.on_event("startup")
def _check_config() -> None:
    if not APP_PASSWORD:
        raise RuntimeError(
            "APP_PASSWORD environment variable is not set — refusing to start "
            "without a password configured."
        )
    os.makedirs(RUNS_ROOT, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/login")
def login(password: str = Form(...)) -> JSONResponse:
    if not secrets.compare_digest(password, APP_PASSWORD):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = serializer.dumps({"ok": True})
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        "session",
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )
    return resp


@app.post("/api/logout")
def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session")
    return resp


@app.get("/api/me")
def me(_: None = Depends(require_auth)) -> JSONResponse:
    return JSONResponse({"ok": True})


@app.post("/api/run")
async def run_pipeline(
    file: UploadFile,
    fmt: str = Form(None),
    _: None = Depends(require_auth),
) -> JSONResponse:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (25 MB limit)")

    _cleanup_old_runs()

    run_id = uuid.uuid4().hex
    run_dir = os.path.join(RUNS_ROOT, run_id)
    input_dir = os.path.join(run_dir, "input")
    output_dir = os.path.join(run_dir, "output")
    os.makedirs(input_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    input_path = os.path.join(input_dir, f"source{ext}")
    with open(input_path, "wb") as f:
        f.write(content)

    try:
        result = await run_in_threadpool(
            pipeline.run, input_path, output_root=output_dir, fmt=fmt or None
        )
    except Exception as exc:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc))

    course_dir = result["course_dir"]
    zip_base = os.path.join(run_dir, "course-package")
    shutil.make_archive(zip_base, "zip", course_dir)

    built = result["built"]
    analysis = built["course_analysis"]
    report_path = os.path.join(course_dir, "reports", "COURSE_ENHANCEMENT_REPORT.md")
    report_text = ""
    if os.path.isfile(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()

    return JSONResponse(
        {
            "run_id": run_id,
            "title": result["normalized"]["course"]["title"],
            "total_lessons": analysis["total_lessons"],
            "total_modules": analysis["total_modules"],
            "no_enhancement_count": analysis["lessons_requiring_no_enhancement"],
            "enhancements_generated": len(built["all_accepted"]),
            "enhancements_suppressed": len(built["all_rejected"]),
            "odoo_module_count": len(result["odoo_requirements"]["modules"]),
            "report_markdown": report_text,
            "download_url": f"/api/download/{run_id}",
        }
    )


@app.get("/api/download/{run_id}")
def download(run_id: str, _: None = Depends(require_auth)) -> FileResponse:
    if not run_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid run id")
    zip_path = os.path.join(RUNS_ROOT, run_id, "course-package.zip")
    if not os.path.isfile(zip_path):
        raise HTTPException(status_code=404, detail="Run not found or expired")
    return FileResponse(zip_path, media_type="application/zip", filename=f"course-package-{run_id[:8]}.zip")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
