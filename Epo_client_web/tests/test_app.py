"""test_app.py

EPO CodeFest – Unit tests for `app.py`
-------------------------------------
These tests validate:
- Helper functions (pure logic).
- The Flask route behaviour, without depending on HTML templates.
- No real HTTP calls: `requests.post` is mocked.

Key testing strategy
--------------------
`app.index()` returns `render_template(...)`, which normally renders Jinja HTML.
In unit tests we patch `app.render_template` to return a simple string ("OK"),
and then we assert on the *arguments* passed to `render_template` (the context).

This avoids:
- needing a `templates/` directory
- JSON serialization issues (the context contains Python `type` objects in FIELDS)

How to run:
    python -m unittest -v
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from unittest.mock import patch, MagicMock
import requests

import app as webapp


class TestHelpers(unittest.TestCase):
    """Unit tests for helper functions (no Flask request context needed)."""

    def test_build_url_defaults_and_sanitization(self):
        # Invalid scheme -> fallback to http.
        # Empty host/port -> defaults.
        # IMPORTANT: build_url currently does `context = (context or "epo_roi").strip()`.
        # If you pass a whitespace-only string, it is truthy and becomes "" after strip,
        # so the final URL ends with `/api_h7/` (no context).
        url = webapp.build_url("ftp", "   ", "  ", "")
        self.assertEqual(url, "http://localhost:8000/api_h7/epo_roi")

        url_whitespace_context = webapp.build_url("http", "localhost", "8000", "   ")
        self.assertEqual(url_whitespace_context, "http://localhost:8000/api_h7/")

        # Valid https and custom values
        url2 = webapp.build_url("https", "example.org", "443", "myctx")
        self.assertEqual(url2, "https://example.org:443/api_h7/myctx")

    def test_parse_value_empty_returns_none(self):
        v, err = webapp.parse_value("log_family_size", "   ", float)
        self.assertIsNone(v)
        self.assertIsNone(err)

    def test_parse_value_invalid_cast_returns_error(self):
        v, err = webapp.parse_value("log_family_size", "not-a-number", float)
        self.assertIsNone(v)
        self.assertIsNotNone(err)
        self.assertIn("Invalid value", err)

    def test_parse_value_range_checks_min_max(self):
        v, err = webapp.parse_value("is_active_recent", "-1", int)
        self.assertIsNone(v)
        self.assertIn("must be ≥", err)

        v2, err2 = webapp.parse_value("novelty_x_breadth", "1.5", float)
        self.assertIsNone(v2)
        self.assertIn("must be ≤", err2)

        v3, err3 = webapp.parse_value("novelty_x_breadth", "0.75", float)
        self.assertEqual(v3, 0.75)
        self.assertIsNone(err3)

    def test_build_payload_from_form_includes_only_non_empty_fields(self):
        form = {
            "is_active_recent": "1",
            "log_legal_events_count": "",
            "log_family_size": "2.0",
        }
        payload, errors = webapp.build_payload_from_form(form)
        self.assertEqual(errors, {})
        self.assertEqual(payload["is_active_recent"], [1])
        self.assertEqual(payload["log_family_size"], [2.0])
        self.assertNotIn("log_legal_events_count", payload)

    def test_build_payload_from_form_reports_validation_errors(self):
        form = {"log_family_size": "999999"}  # violates max 7.0
        payload, errors = webapp.build_payload_from_form(form)
        self.assertEqual(payload, {})
        self.assertIn("log_family_size", errors)


class TestFlaskRoute(unittest.TestCase):
    """Unit tests for the Flask route using Flask's test client."""

    def setUp(self):
        webapp.HISTORY.clear()
        webapp.app.testing = True
        self.client = webapp.app.test_client()

    @staticmethod
    def _ok_template(_template_name: str, **_context):
        # Return a simple string so Flask doesn't try to JSON-serialize the context.
        return "OK"

    @patch.object(webapp, "render_template")
    def test_index_get_renders_default_context(self, mock_render):
        mock_render.side_effect = self._ok_template

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_data(as_text=True), "OK")

        # Assert what was passed into render_template
        _tmpl, kwargs = mock_render.call_args
        ctx = kwargs

        self.assertEqual(ctx["scheme"], "http")
        self.assertEqual(ctx["host"], "localhost")
        self.assertEqual(ctx["port"], "8000")
        self.assertEqual(ctx["context"], "epo_roi")
        self.assertIn("fields", ctx)
        self.assertIn("ranges", ctx)
        self.assertIn("history", ctx)

    @patch.object(webapp, "render_template")
    def test_index_post_with_no_features_shows_validation_error(self, mock_render):
        mock_render.side_effect = self._ok_template

        resp = self.client.post("/", data={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_data(as_text=True), "OK")

        _tmpl, kwargs = mock_render.call_args
        ctx = kwargs

        self.assertIn("errors", ctx)
        self.assertIn("_global", ctx["errors"])  # "Please provide at least one feature value."
        self.assertEqual(len(webapp.HISTORY), 0)  # no API call

    @patch.object(webapp, "render_template")
    @patch.object(webapp.requests, "post")
    def test_index_post_success_calls_api_and_records_history(self, mock_post, mock_render):
        mock_render.side_effect = self._ok_template

        fake_response = MagicMock()
        fake_response.ok = True
        fake_response.status_code = 200
        fake_response.json.return_value = {"roi": 0.42}
        mock_post.return_value = fake_response

        resp = self.client.post("/", data={"is_active_recent": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_data(as_text=True), "OK")

        _tmpl, kwargs = mock_render.call_args
        ctx = kwargs

        effective_url = ctx["effective_url"]
        self.assertTrue(effective_url.endswith("/api_h7/epo_roi"))

        mock_post.assert_called_once()
        called_url = mock_post.call_args.kwargs.get("url") or mock_post.call_args.args[0]
        self.assertEqual(called_url, effective_url)

        called_json = mock_post.call_args.kwargs.get("json")
        self.assertEqual(called_json, {"is_active_recent": [1]})

        self.assertEqual(ctx["result_json"], {"roi": 0.42})
        self.assertEqual(ctx["status_code"], 200)

        self.assertEqual(len(webapp.HISTORY), 1)
        self.assertTrue(webapp.HISTORY[0].ok)

    @patch.object(webapp, "render_template")
    @patch.object(webapp.requests, "post")
    def test_index_post_http_error_records_error_in_history(self, mock_post, mock_render):
        mock_render.side_effect = self._ok_template

        fake_response = MagicMock()
        fake_response.ok = False
        fake_response.status_code = 500
        fake_response.text = "Internal Server Error"
        mock_post.return_value = fake_response

        resp = self.client.post("/", data={"is_active_recent": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_data(as_text=True), "OK")

        _tmpl, kwargs = mock_render.call_args
        ctx = kwargs

        self.assertIsNotNone(ctx["error_global"])
        self.assertIn("HTTP 500", ctx["error_global"])

        self.assertEqual(len(webapp.HISTORY), 1)
        self.assertFalse(webapp.HISTORY[0].ok)
        self.assertEqual(webapp.HISTORY[0].status_code, 500)

    @patch.object(webapp, "render_template")
    @patch.object(webapp.requests, "post", side_effect=requests.RequestException("timeout"))
    def test_index_post_request_exception_records_error(self, mock_post, mock_render):
        mock_render.side_effect = self._ok_template

        resp = self.client.post("/", data={"is_active_recent": "1", "timeout": "0.001"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_data(as_text=True), "OK")

        _tmpl, kwargs = mock_render.call_args
        ctx = kwargs

        self.assertIsNotNone(ctx["error_global"])
        self.assertIn("API error", ctx["error_global"])

        self.assertEqual(len(webapp.HISTORY), 1)
        self.assertFalse(webapp.HISTORY[0].ok)
        self.assertIsNone(webapp.HISTORY[0].status_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
