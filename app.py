from __future__ import annotations

import json
import mimetypes
import re
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
UPSTREAM_DIR = BASE_DIR / "upstream"
STATIC_DIR = BASE_DIR / "static"
VENDOR_DIR = BASE_DIR / ".vendor"

if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))
if str(UPSTREAM_DIR) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_DIR))

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import YouTubeTranscriptApiException
except ModuleNotFoundError as exc:  # pragma: no cover - startup guard
    missing = exc.name or "dependency"
    raise SystemExit(
        f"Missing Python dependency: {missing}. Run `python -m pip install -r requirements.txt`."
    ) from exc


VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    snippet_count: int
    duration_seconds: float


def extract_video_id(value: str) -> str:
    candidate = value.strip()
    if VIDEO_ID_RE.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)
    host = parsed.netloc.lower().removeprefix("www.")
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        if VIDEO_ID_RE.fullmatch(query_id):
            return query_id
        if path_parts and path_parts[0] in {"shorts", "embed", "live"}:
            possible_id = path_parts[1] if len(path_parts) > 1 else ""
            if VIDEO_ID_RE.fullmatch(possible_id):
                return possible_id

    if host == "youtu.be" and path_parts and VIDEO_ID_RE.fullmatch(path_parts[0]):
        return path_parts[0]

    raise ValueError("Không nhận diện được video ID từ link này.")


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def normalize_languages(value: Any) -> list[str]:
    if isinstance(value, list):
        languages = value
    elif isinstance(value, str):
        languages = value.split(",")
    else:
        languages = ["vi", "en"]

    cleaned = [item.strip().lower() for item in languages if str(item).strip()]
    return cleaned or ["vi", "en"]


def fetch_transcript(video_url: str, with_timestamps: bool, languages: list[str]) -> TranscriptResult:
    video_id = extract_video_id(video_url)
    transcript = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    snippets = list(transcript)

    if with_timestamps:
        text = "\n".join(
            f"[{format_timestamp(snippet.start)}] {snippet.text}" for snippet in snippets
        )
    else:
        text = "\n".join(snippet.text for snippet in snippets)

    duration_seconds = 0.0
    if snippets:
        last_snippet = snippets[-1]
        duration_seconds = float(last_snippet.start + last_snippet.duration)

    return TranscriptResult(
        text=text,
        video_id=video_id,
        language=transcript.language,
        language_code=transcript.language_code,
        is_generated=transcript.is_generated,
        snippet_count=len(snippets),
        duration_seconds=duration_seconds,
    )


class TranscriptAppHandler(BaseHTTPRequestHandler):
    server_version = "TranscriptStudio/1.0"

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.serve_static("index.html")
            return

        requested = self.path.split("?", 1)[0].lstrip("/")
        if not requested.startswith("static/"):
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        self.serve_static(requested.removeprefix("static/"))

    def do_POST(self) -> None:
        if self.path != "/api/transcript":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            payload = self.read_json()
            video_url = str(payload.get("url", "")).strip()
            if not video_url:
                raise ValueError("Vui lòng nhập link YouTube.")

            result = fetch_transcript(
                video_url=video_url,
                with_timestamps=bool(payload.get("timestamps", False)),
                languages=normalize_languages(payload.get("languages", ["vi", "en"])),
            )
            self.send_json(
                {
                    "ok": True,
                    "transcript": result.text,
                    "videoId": result.video_id,
                    "language": result.language,
                    "languageCode": result.language_code,
                    "isGenerated": result.is_generated,
                    "snippetCount": result.snippet_count,
                    "durationSeconds": result.duration_seconds,
                }
            )
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except YouTubeTranscriptApiException as exc:
            self.send_json({"ok": False, "error": str(exc).strip()}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive server boundary
            self.send_json(
                {"ok": False, "error": f"Lỗi không mong muốn: {exc}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, filename: str) -> None:
        path = (STATIC_DIR / filename).resolve()
        if not path.is_file() or STATIC_DIR.resolve() not in path.parents:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), TranscriptAppHandler)
    startup_message = f"Transcript Studio is running at http://{host}:{port}"
    try:
        print(startup_message)
    except Exception:
        pass
    try:
        (BASE_DIR / "server.log").write_text(startup_message + "\n", encoding="utf-8")
    except OSError:
        pass
    server.serve_forever()


if __name__ == "__main__":
    run()
