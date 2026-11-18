from pathlib import Path
from time import perf_counter
import json
import uuid

from flask import Flask, jsonify, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from utils.database import add_request, clear_history, get_history, init_db
from utils.detector import VehicleDetector
from utils.exporters import export_history_to_excel, export_history_to_pdf


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
RESULT_DIR = BASE_DIR / "static" / "results"
REPORT_DIR = BASE_DIR / "reports"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "mov", "avi", "mkv"}

for folder in (UPLOAD_DIR, RESULT_DIR, REPORT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024

init_db()
detector = VehicleDetector(BASE_DIR / "yolov8n.pt")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def number(name, default, value_type=float):
    try:
        return value_type(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/process")
def process_file():
    uploaded = request.files.get("media")
    if uploaded is None or not uploaded.filename:
        return jsonify(success=False, error="Выберите изображение или видео."), 400
    if not allowed_file(uploaded.filename):
        return jsonify(success=False, error="Поддерживаются JPG, PNG, WEBP, MP4, MOV, AVI и MKV."), 400

    original_name = secure_filename(uploaded.filename) or "media"
    extension = Path(original_name).suffix.lower()
    file_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{file_id}{extension}"
    output_extension = ".jpg" if extension in {".jpg", ".jpeg", ".png", ".webp"} else ".mp4"
    output_path = RESULT_DIR / f"{file_id}_result{output_extension}"
    uploaded.save(input_path)

    settings = {
        "stop_line_percent": max(10, min(number("stop_line_percent", 70), 95)),
        "confidence": max(0.15, min(number("confidence", 0.35), 0.9)),
        "light_mode": request.form.get("light_mode", "red"),
        "roi": [
            number("roi_x", 0, int),
            number("roi_y", 0, int),
            number("roi_w", 0, int),
            number("roi_h", 0, int),
        ],
    }

    started = perf_counter()
    try:
        stats = detector.process(input_path, output_path, **settings)
    except Exception as error:
        input_path.unlink(missing_ok=True)
        return jsonify(success=False, error=f"Ошибка обработки: {error}"), 500

    processing_time = round(perf_counter() - started, 2)
    result_url = url_for("static", filename=f"results/{output_path.name}")
    request_id = add_request(
        original_filename=uploaded.filename,
        media_type=stats["media_type"],
        vehicle_count=stats["vehicle_count"],
        violation_count=stats["violation_count"],
        red_light=stats["red_light"],
        processing_time=processing_time,
        result_url=result_url,
        details=json.dumps(stats["class_counts"], ensure_ascii=False),
    )

    return jsonify(
        success=True,
        request_id=request_id,
        result_url=result_url,
        processing_time=processing_time,
        **stats,
    )


@app.get("/api/history")
def history():
    return jsonify(success=True, records=get_history(limit=50))


@app.post("/api/clear-history")
def clear_history_route():
    clear_history()
    return jsonify(success=True)


@app.get("/export/excel")
def export_excel():
    path = export_history_to_excel(get_history(limit=1000), REPORT_DIR)
    return send_file(path, as_attachment=True, download_name="red_light_history.xlsx")


@app.get("/export/pdf")
def export_pdf():
    path = export_history_to_pdf(get_history(limit=1000), REPORT_DIR)
    return send_file(path, as_attachment=True, download_name="red_light_history.pdf")


@app.get("/export/json")
def export_json():
    path = REPORT_DIR / "red_light_history.json"
    path.write_text(json.dumps(get_history(limit=1000), ensure_ascii=False, indent=2), encoding="utf-8")
    return send_file(path, as_attachment=True, download_name=path.name)


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(success=False, error="Файл превышает 250 МБ."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
