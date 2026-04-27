import os
import unittest

from fastapi.testclient import TestClient


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Ensure any configured LLM key won't break tests (we validate fallback path).
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        from app.main import app  # local import so env vars apply

        cls.client = TestClient(app)
        cls._ctx = cls.client.__enter__()

    def test_homepage_renders(self) -> None:
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Student Course Advisor", r.text)
        self.assertIn("Top course matches", r.text)

    def test_match_endpoint(self) -> None:
        payload = {
            "student": {"subjects": ["CS"], "days": "TR", "only_open": True, "interests": ""},
            "top_n": 3,
            "max_per_subject": 3,
        }
        r = self.client.post("/api/match", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)
        self.assertTrue(len(data["results"]) >= 1)
        first = data["results"][0]
        self.assertIn("course", first)
        self.assertIn("score_total", first)
        self.assertIn("score_breakdown", first)
        self.assertIn("reasons", first)

    def test_ask_endpoint_fallback(self) -> None:
        r = self.client.post("/api/ask", json={"question": "What CS courses have open seats on TR?"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("advice", data)
        self.assertIn("courses", data)

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "client"):
            cls.client.__exit__(None, None, None)


if __name__ == "__main__":
    unittest.main()

