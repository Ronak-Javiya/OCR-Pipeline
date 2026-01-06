from pathlib import Path

def stream_pdf_pages(pdf_path, dpi=150):
    import fitz
    from PIL import Image
    import numpy as np

    doc = fitz.open(pdf_path)

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_index, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        yield page_index, np.array(img)

    doc.close()

def stream_batches(page_stream, batch_size):
    batch_imgs = []
    batch_indices = []

    for page_index, img in page_stream:
        batch_imgs.append(img)
        batch_indices.append(page_index)

        if len(batch_imgs) == batch_size:
            yield batch_indices, batch_imgs
            batch_imgs, batch_indices = [], []

    if batch_imgs:
        yield batch_indices, batch_imgs


def pdf_to_images(pdf_path, dpi=200):
    import fitz
    from PIL import Image
    import numpy as np

    doc = fitz.open(pdf_path)
    images = []

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        images.append(np.array(img))

    doc.close()
    return images

def batch_iter(items, batch_size):
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

import json

import zipfile

def zip_output(output_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in output_dir.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(output_dir))


def extract_text_from_pdf(pdf_path, job_id, original_filename, ocr):
    from job_state import write_job
    from pathlib import Path
    import json

    output_path = Path(f"output/{job_id}")
    output_path.mkdir(parents=True, exist_ok=True)

    write_job(job_id, {"status": "running", "progress": 0, "error": None})

    markdown_list = []
    json_list = []
    markdown_images = []

    # Count pages once (cheap)
    import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    batch_size = 8
    processed_pages = 0

    page_stream = stream_pdf_pages(pdf_path, dpi=150)

    try:
        for page_indices, images in stream_batches(page_stream, batch_size):
            output = ocr.predict(images)

            for res in output:
                markdown_list.append(res.markdown)
                json_list.append(res.json)
                markdown_images.append(res.markdown.get("markdown_images", {}))

            processed_pages += len(page_indices)
            progress = int((processed_pages / total_pages) * 100)

            write_job(job_id, {
                "status": "running",
                "progress": min(progress, 99),
                "error": None
            })


        markdown_texts = ocr.concatenate_markdown_pages(markdown_list)

        file_stem = Path(original_filename).stem if original_filename else Path(pdf_path).stem

        mkd_file_path = output_path / f"{file_stem}.md"
        mkd_file_path.parent.mkdir(parents=True, exist_ok=True)
        json_file_path = output_path / f"{file_stem}.json"
        json_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(mkd_file_path, "w", encoding="utf-8") as f:
            f.write(markdown_texts)

        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(json_list, f, ensure_ascii=False, indent=4)

        for item in markdown_images:
            if item:
                for path, image in item.items():
                    file_path = output_path / path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    image.save(file_path)

        zip_path = output_path.parent / f"{Path(job_id).stem}.zip"
        zip_output(output_path, zip_path)

        write_job(job_id, {
            "status": "done",
            "progress": 100,
            "error": None
        })

    except Exception as e:
        write_job(job_id, {
            "status": "failed",
            "progress": 0,
            "error": str(e)
        })

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import uuid, tempfile, shutil
from multiprocessing import Process
from job_state import init_job, read_job

app = FastAPI(title="Qwen-VL PDF OCR API")

@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    job_id = uuid.uuid4().hex
    init_job(job_id, file.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        pdf_path = tmp.name

    JOB_QUEUE.put((pdf_path, job_id, file.filename))

    return {
        "job_id": job_id,
        "status_url": f"/status/{job_id}",
        "download_url": f"/download/{job_id}"
    }

    
@app.get("/status/{job_id}")
def status(job_id: str):
    job = read_job(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    return job

@app.get("/download/{job_id}")
def download(job_id: str):
    zip_path = Path("output") / f"{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(404, "Not ready")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="result.zip"
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"➡️  Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"⬅️  Response status: {response.status_code}")
    return response

@app.get("/health")
def health():
    print("✅ Health check hit")
    return {"status": "ok"}

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>OCR Dashboard</title>
  <style>
    body { font-family: Arial; margin: 40px; }
    button { padding: 10px 20px; }
    #progress { margin-top: 20px; }
    #log { white-space: pre-line; margin-top: 10px; }
  </style>
</head>
<body>

<h2>PDF OCR Dashboard</h2>

<input type="file" id="file" accept="application/pdf">
<button onclick="start()">Start OCR</button>

<div id="progress"></div>
<div id="log"></div>

<script>
let jobId = null;

async function start() {
  const fileInput = document.getElementById("file");
  if (!fileInput.files.length) {
    alert("Select a PDF");
    return;
  }

  const form = new FormData();
  form.append("file", fileInput.files[0]);

  document.getElementById("log").innerText = "Uploading...";

  const res = await fetch("/extract", { method: "POST", body: form });
  const data = await res.json();

  jobId = data.job_id;
  document.getElementById("log").innerText = "Job ID: " + jobId;

  poll();
}

async function poll() {
  if (!jobId) return;

  const res = await fetch(`/status/${jobId}`);
  const data = await res.json();

  document.getElementById("progress").innerText =
    `Status: ${data.status}, Progress: ${data.progress}%`;

  if (data.status === "done") {
    document.getElementById("log").innerHTML =
      `<a href="/download/${jobId}">Download Result ZIP</a>`;
  } else if (data.status === "failed") {
    document.getElementById("log").innerText = "Error: " + data.error;
  } else {
    setTimeout(poll, 2000);
  }
}
</script>

</body>
</html>
"""

from multiprocessing import Queue

JOB_QUEUE = Queue(maxsize=10)  # prevent overload
def ocr_worker(job_queue: Queue):
    from paddleocr import PPStructureV3
    from job_state import write_job

    # Load models ONCE
    ocr = PPStructureV3(
        lang="en",
        device="gpu",
        use_chart_recognition=True,
        use_doc_unwarping=True,
        use_doc_orientation_classify=True,
        use_formula_recognition=True,
        use_region_detection=True,
        use_seal_recognition=True,
        use_table_recognition=True,
        use_textline_orientation=True
    )

    print("✅ OCR worker ready")

    while True:
        job = job_queue.get()   # BLOCKS until job arrives
        if job is None:
            break  # graceful shutdown

        pdf_path, job_id, filename = job

        try:
            extract_text_from_pdf(
                pdf_path=pdf_path,
                job_id=job_id,
                original_filename=filename,
                ocr=ocr   # IMPORTANT: reuse model
            )
        except Exception as e:
            write_job(job_id, {
                "status": "failed",
                "progress": 0,
                "error": str(e)
            })

from multiprocessing import Process

WORKER = Process(
    target=ocr_worker,
    args=(JOB_QUEUE,),
    daemon=True
)
WORKER.start()
