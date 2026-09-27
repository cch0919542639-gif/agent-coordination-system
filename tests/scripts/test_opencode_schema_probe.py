import importlib.util
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location("probe", Path(__file__).resolve().parents[2] / "scripts/opencode_schema_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_digest_mismatch_never_spawns(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "binary"
            binary.write_bytes(b"fixture")
            with patch.object(probe.subprocess, "Popen") as spawn:
                self.assertEqual(probe.probe(binary, "0" * 64)["decision"], "denied_binary_digest")
                spawn.assert_not_called()

    def test_schema_omits_examples_and_unselected_endpoints(self):
        document = {"paths": {"/permission": {"get": {"responses": {"200": {"content": {"application/json": {"schema": {"type": "array", "items": {"type": "string", "example": "private"}}}}}}}}, "/config": {"get": {"private": "secret"}}}}
        result = probe.summarize(document)
        self.assertNotIn("private", str(result))
        self.assertEqual(list(result), ["/permission"])

    def test_no_matching_schema_fails_closed(self):
        with self.assertRaises(ValueError):
            probe.summarize({"paths": {"/unrelated": {}}})
        with self.assertRaises(ValueError):
            probe.summarize({"paths": {"/permission": {}}})

    def test_trickling_response_obeys_deadline(self):
        response = MagicMock()
        response.read1.return_value = b" "
        with patch.object(probe.time, "monotonic", side_effect=[0, 1, 2, 4]):
            with self.assertRaises(TimeoutError):
                probe.read_json(response, 3)
        self.assertEqual(response.read1.call_count, 2)

    def test_stuck_headers_do_not_block_supervisor(self):
        release = threading.Event()
        opener = MagicMock()
        def slow_open(*args, **kwargs):
            release.wait(2)
            raise TimeoutError()
        opener.open.side_effect = slow_open
        try:
            with self.assertRaises(TimeoutError):
                probe.bounded_get(opener, None, time.monotonic() + 0.02)
        finally:
            release.set()

    def run_mocked_probe(self, *, teardown_failure=False, read_timeout=False):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "binary"
            binary.write_bytes(b"fixture")
            child = MagicMock()
            child.poll.return_value = None
            opener = MagicMock()
            document = {"paths": {"/permission": {"get": {"responses": {"200": {"content": {"application/json": {"schema": {"type": "array"}}}}}}}}}
            responses = [io.BytesIO(json.dumps(value).encode()) for value in ({"healthy": True, "version": "1.18.32"}, document)]
            opener.open.side_effect = responses
            with patch.object(probe.subprocess, "Popen", return_value=child) as spawn, \
                 patch.object(probe.subprocess, "run") as stop, \
                 patch.object(probe.urllib.request, "build_opener", return_value=opener), \
                 patch.object(probe.socket, "socket"):
                if teardown_failure:
                    child.wait.side_effect = TimeoutError()
                if read_timeout:
                    opener.open.side_effect = [responses[0], TimeoutError()]
                result = probe.probe(binary, hashlib.sha256(b"fixture").hexdigest())
                spawn.assert_called_once()
                self.assertEqual([call.args[0].get_method() for call in opener.open.call_args_list], ["GET", "GET"])
                self.assertEqual([call.args[0].selector for call in opener.open.call_args_list], ["/global/health", "/doc"])
                child.wait.assert_called_once()
                if probe.os.name == "nt":
                    stop.assert_called_once()
                else:
                    child.terminate.assert_called_once()
                return result

    def test_success_stops_owned_server(self):
        result = self.run_mocked_probe()
        self.assertEqual(result["decision"], "schema_observed")
        self.assertTrue(result["server_stopped"])

    def test_read_timeout_still_stops_owned_server(self):
        result = self.run_mocked_probe(read_timeout=True)
        self.assertEqual(result["decision"], "stopped_probe")
        self.assertTrue(result["server_stopped"])

    def test_teardown_failure_overrides_success(self):
        result = self.run_mocked_probe(teardown_failure=True)
        self.assertEqual(result["decision"], "stopped_teardown_failure")
        self.assertFalse(result["server_stopped"])

    def test_redirect_is_denied(self):
        with self.assertRaises(ValueError):
            probe.NoRedirect().redirect_request(None, None, 302, None, None, "https://example.org")


if __name__ == "__main__":
    unittest.main()
