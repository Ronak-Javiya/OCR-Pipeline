# OCR_Layout

A web-based OCR application for extracting text and layout information from PDF files. This project uses `paddleocr` for high-accuracy text and layout recognition and provides a simple `FastAPI` web interface for uploading PDFs and retrieving the results.

## Features

-   **PDF to Text and Layout:** Extracts text, tables, and other structural information from PDF files.
-   **Multiple Output Formats:** Generates both Markdown and JSON output for easy integration with other tools.
-   **Web Interface:** A simple dashboard to upload PDFs and monitor the OCR process.
-   **REST API:** A simple API for programmatic access to the OCR functionality.
-   **Asynchronous Processing:** Uses a background worker to process OCR jobs without blocking the API.

## Technology Stack

-   **Backend:** [FastAPI](https://fastapi.tiangolo.com/)
-   **OCR Engine:** [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (specifically PP-StructureV3)
-   **PDF Processing:** [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
-   **Web Server:** [Uvicorn](https://www.uvicorn.org/)

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd OCR_Layout
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **GPU Requirements:**
    `paddleocr` is configured to run on a GPU (`device="gpu"`) for better performance. Ensure you have a compatible NVIDIA GPU and the necessary CUDA drivers installed. If you don't have a GPU, you can change the device to `"cpu"` in `main.py`, but processing will be significantly slower.

## Usage

1.  **Run the application:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
    The application will be available at `http://0.0.0.0:8000`.

2.  **Use the web interface:**
    -   Open your browser and navigate to `http://0.0.0.0.:8000`.
    -   Select a PDF file and click "Start OCR".
    -   The progress of the OCR job will be displayed.
    -   Once complete, a download link for the results (a ZIP file containing the Markdown and JSON files) will appear.

## API Endpoints

-   `GET /`: The main dashboard to upload PDFs.
-   `POST /extract`: Upload a PDF file to start an OCR job.
    -   **File:** The PDF file to process.
    -   **Returns:** A JSON object with the `job_id`, `status_url`, and `download_url`.
-   `GET /status/{job_id}`: Check the status of an OCR job.
    -   **Returns:** A JSON object with the job status, progress, and any errors.
-   `GET /download/{job_id}`: Download the results of a completed OCR job.
    -   **Returns:** A ZIP file containing the extracted text in Markdown and JSON formats.
-   `GET /health`: A health check endpoint.
    -   **Returns:** `{"status": "ok"}`