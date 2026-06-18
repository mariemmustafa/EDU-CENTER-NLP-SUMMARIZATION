# Text Summarization Platform

## Project Overview

Production-grade microservices system for extracting and summarizing text from PDF, DOCX, PPTX, and TXT documents. It provides an API gateway for handling uploads and an NLP service for actual summarization utilizing HuggingFace or OpenAI.

## Features

- Multi-format document upload (PDF, DOCX, PPTX, TXT) with up to 10 MB limit.
- Arabic summarization support via multilingual models (e.g. `t5-arabic-text-summarization`) and OpenAI fallback.
- Advanced NLP processing including sentencepiece, protobuf support, repetition penalty, and no repeat n-gram size control.
- Multilingual routing and intelligent provider fallback chain.
- Improved PDF text cleaning and output validation.
- Clean Architecture with dependency injection.
- Structured error handling, request tracing, and retry logic.
- API Key authentication and Rate limiting.

## Architecture

```text
                        ┌─────────────┐
        Client ──────►  │    Nginx    │  (port 80 — production)
                        │   Reverse   │
                        │    Proxy    │
                        └──────┬──────┘
                                │
┌──────────────┐       HTTP    │        ┌──────────────┐
│              │  ◄────────────┘  ───►  │              │
│  API Gateway │   POST /api/v1/        │ NLP Service  │
│  (Express)   │   summarize            │  (FastAPI)   │
│  Port 3000   │  ◄──────────────────   │  Port 8000   │
│              │   JSON response        │              │
└──────┬───────┘                        └──────┬───────┘
       │                                       │
  Multi-format                         Summarization
  Uploads                              HuggingFace or
  (PDF, DOCX,                          OpenAI Provider
  PPTX, TXT)                           
```

## API Endpoint

**POST /api/v1/summarize**

Extracts and summarizes text from a document.

**Headers:**
- `x-api-key`: Your API key (if configured)

**Request** (multipart/form-data):
- `file`: Document file (PDF, DOCX, PPTX, TXT - max 10 MB)
- `start_page`: First page (1-based)
- `end_page`: Last page (1-based)

## Installation

### Prerequisites
- Docker & Docker Compose

Clone the repository and configure environment variables:
```bash
git clone https://github.com/mariemmustafa/EDU-CENTER-NLP-SUMMARIZATION.git
cd EDU-CENTER-NLP-SUMMARIZATION
```

## Local Run Instructions

To run the platform locally using Docker Compose:

```bash
docker compose up --build
```

> Note: First startup downloads the HuggingFace model (~1.6 GB). Allow 2-3 minutes.

To verify it is running:
```bash
curl http://localhost:3000/health
```

## Example Request

```bash
curl -X POST http://localhost:3000/api/v1/summarize \
  -H "x-api-key: your-api-key" \
  -F "file=@document.pdf" \
  -F "start_page=1" \
  -F "end_page=3"
```

## Deployment Notes

To deploy for production, start the services using the production overlay which includes Nginx:

```bash
export API_KEY=your-secret-api-key
export ALLOWED_ORIGINS=https://your-frontend.com

docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Alternatively, use the provided deployment script:

```bash
API_KEY=your-secret-key bash deploy.sh prod
```

Ensure that your `SUMMARIZATION_PROVIDER` and `OPENAI_API_KEY` are properly configured in `.env` if utilizing OpenAI for production fallback or Arabic text summarization.
## Daily Run Commands (After Setup)

Every time you run the project:

```bash
cd nlp-service
venv\Scripts\activate
python -m uvicorn main:app --reload
http://127.0.0.1:8000/docs

```
