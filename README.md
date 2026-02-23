# EML to PDF API

Small HTTP service that converts EML (email) files to PDF using [eml2pdf](https://pypi.org/project/eml2pdf/). Intended for use from n8n or any client that can send raw binary and receive a PDF.

## Use case

This API exists for workflows (e.g. with [n8n](https://n8n.io)) where you need to convert EML emails to PDF **on your own infrastructure**. There is no simple, easy-to-install converter that runs inside a typical n8n (Node.js) container—[eml2pdf](https://pypi.org/project/eml2pdf/) depends on Python and system libraries (Pango/Cairo). So this project runs as a **separate container** next to n8n: you POST raw EML bytes and get a PDF back. n8n calls the API via an HTTP Request node.

**Why there is no authentication:** The service is designed to run on a **private Docker network** where only your own stack (e.g. n8n) can reach it. It is not meant to be exposed to the internet. In that setting, adding API keys or auth would add complexity without real benefit. If you ever expose the port publicly, put a reverse proxy with authentication in front of it.

---

## Deploy from GitHub (e.g. on your server with n8n)

1. Clone this repo next to your existing `docker-compose.yml` (e.g. both in `n8n`’s home):
   ```bash
   git clone https://github.com/steineggerroland/eml2pdf-api.git
   ```
2. Edit your existing `docker-compose.yml` and add the **eml2pdf-api** service. Copy the block from **docker-compose.snippet.yml** (the `eml2pdf-api` entry). Set `build` to the clone path, e.g. `build: ./eml2pdf-api` if the compose file is in the same directory as the clone’s parent.
3. Start the container:
   ```bash
   docker compose up -d --build eml2pdf-api
   ```
   n8n can then call `http://eml2pdf-api:8080/convert` on the same Docker network.

## Run with Docker Compose (standalone)

```bash
docker compose up -d --build
```

Service listens on **port 8080**. From the same host: `http://localhost:8080`.

## API

- **`POST /convert`**  
  - **Body:** raw EML file bytes (binary).  
  - **Response:** PDF file (`Content-Type: application/pdf`).

- **Query parameters (optional):**
  - `page` – Page size, e.g. `a4`, `a4 landscape`, `letter`, `a3`. Default: `a4`.
  - `debug_html` – Set to `1` or `true` to keep intermediate HTML (for debugging).
  - `unsafe` – Set to `1` or `true` to skip HTML sanitization (use only for trusted EML).

- **`GET /health`**  
  Returns `{"status":"ok"}` for liveness/readiness.

### Example (curl)

```bash
curl -X POST "http://localhost:8080/convert?page=a4%20landscape" \
  --data-binary @message.eml \
  -o out.pdf
```

## n8n integration

1. **Same Docker Compose:** Add your n8n service to this `docker-compose.yml` (or add this service to your existing n8n compose). All services share one network; n8n can call `http://eml2pdf-api:8080/convert`.

2. **HTTP Request node:**
   - Method: **POST**
   - URL: `http://eml2pdf-api:8080/convert` (or `http://localhost:8080/convert` if n8n runs on the host).
   - Body: **Binary Data**, select the item/binary that contains the EML file (e.g. from “Read Binary File” or email attachment).
   - Optional: add query parameters in the URL, e.g. `?page=a4%20landscape`.

3. The node output will be the PDF binary; use it in the next node (e.g. save to disk, send to Paperless, etc.).

## No authentication

This service does not implement authentication. Run it only on a trusted network (e.g. Docker network or localhost) and do not expose port 8080 to the internet unless you add a reverse proxy with auth.

## Local development (without Docker)

Requires Python 3.11+, Pango/Cairo (e.g. on macOS: `brew install pango`), then:

```bash
pip install -r requirements.txt
PORT=8080 python app.py
```
