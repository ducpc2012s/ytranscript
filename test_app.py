import unittest
from types import SimpleNamespace

from app import extract_video_id, format_timestamp, fetch_transcript


class FakeTranscript:
    language = "Vietnamese"
    language_code = "vi"
    is_generated = True

    def __iter__(self):
        return iter(
            [
                SimpleNamespace(text="Xin chào", start=0.0, duration=1.2),
                SimpleNamespace(text="mọi người", start=1.2, duration=2.0),
            ]
        )


class FakeYouTubeTranscriptApi:
    def fetch(self, video_id, languages):
        assert video_id == "dQw4w9WgXcQ"
        assert languages == ["vi", "en"]
        return FakeTranscript()


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

    def test_fetch_transcript_plain(self):
        import app

        original_api = app.YouTubeTranscriptApi
        app.YouTubeTranscriptApi = FakeYouTubeTranscriptApi
        try:
            result = fetch_transcript("https://youtu.be/dQw4w9WgXcQ", False, ["vi", "en"])
        finally:
            app.YouTubeTranscriptApi = original_api

        self.assertEqual(result.text, "Xin chào\nmọi người")
        self.assertEqual(result.snippet_count, 2)
        self.assertEqual(result.duration_seconds, 3.2)


if __name__ == "__main__":
    unittest.main()
