import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app
from app import (
    extract_video_id,
    format_timestamp,
    fetch_transcript,
    get_runtime_config,
    normalize_languages,
)


class FakeTranscript:
    language = "Vietnamese"
    language_code = "vi"
    is_generated = True
    translation_languages = []

    def fetch(self):
        return self

    def __iter__(self):
        return iter(
            [
                SimpleNamespace(text="Xin chào", start=0.0, duration=1.2),
                SimpleNamespace(text="mọi người", start=1.2, duration=2.0),
            ]
        )


class FakeYouTubeTranscriptApi:
    def list(self, video_id):
        assert video_id == "dQw4w9WgXcQ"
        return FakeTranscriptList(FakeTranscript())


class FakeTranscriptList:
    def __init__(self, transcript):
        self.transcript = transcript

    def __iter__(self):
        return iter([self.transcript])

    def find_transcript(self, languages):
        assert languages == ["vi", "en"]
        return self.transcript


class FakeTurkishTranscript(FakeTranscript):
    language = "Turkish (auto-generated)"
    language_code = "tr"
    is_generated = True
    translation_languages = []

    def fetch(self):
        return self


class FakeFallbackTranscriptList:
    def __iter__(self):
        return iter([FakeTurkishTranscript()])

    def find_transcript(self, languages):
        raise app.YouTubeTranscriptApiException("No transcript found")


class FakeFallbackYouTubeTranscriptApi:
    def list(self, video_id):
        assert video_id == "dQw4w9WgXcQ"
        return FakeFallbackTranscriptList()


class TranscriptAppTests(unittest.TestCase):
    def test_extract_video_id_from_watch_url(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_from_short_url(self):
        self.assertEqual(
            extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=10"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_from_shorts_url(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_format_timestamp_with_hours(self):
        self.assertEqual(format_timestamp(3723.9), "01:02:03")

    def test_runtime_config_defaults_to_localhost(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(get_runtime_config(), ("127.0.0.1", 8000))

    def test_runtime_config_uses_deploy_port_and_public_host(self):
        with patch.dict("os.environ", {"PORT": "10000"}, clear=True):
            self.assertEqual(get_runtime_config(), ("0.0.0.0", 10000))

    def test_normalize_languages_filters_invalid_codes(self):
        self.assertEqual(normalize_languages(["=", "languages=en", " VI "]), ["en", "vi"])
        self.assertEqual(normalize_languages("="), [])

    def test_fetch_transcript_plain(self):
        original_api = app.YouTubeTranscriptApi
        app.YouTubeTranscriptApi = FakeYouTubeTranscriptApi
        try:
            result = fetch_transcript("https://youtu.be/dQw4w9WgXcQ", False, ["vi", "en"])
        finally:
            app.YouTubeTranscriptApi = original_api

        self.assertEqual(result.text, "Xin chào\nmọi người")
        self.assertEqual(result.snippet_count, 2)
        self.assertEqual(result.duration_seconds, 3.2)

    def test_fetch_transcript_uses_available_source_language_without_translation(self):
        original_api = app.YouTubeTranscriptApi
        app.YouTubeTranscriptApi = FakeFallbackYouTubeTranscriptApi
        try:
            result = fetch_transcript("https://youtu.be/dQw4w9WgXcQ", False, ["vi", "en"])
        finally:
            app.YouTubeTranscriptApi = original_api

        self.assertEqual(result.language_code, "tr")
        self.assertEqual(result.language, "Turkish (auto-generated)")

    def test_fetch_transcript_uses_first_available_when_no_language_is_requested(self):
        original_api = app.YouTubeTranscriptApi
        app.YouTubeTranscriptApi = FakeFallbackYouTubeTranscriptApi
        try:
            result = fetch_transcript("https://youtu.be/dQw4w9WgXcQ", False, [])
        finally:
            app.YouTubeTranscriptApi = original_api

        self.assertEqual(result.language_code, "tr")


if __name__ == "__main__":
    unittest.main()
