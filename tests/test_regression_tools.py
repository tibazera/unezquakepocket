import json
import pathlib
import struct
import tempfile
import unittest

from tools.regression import demo_regression_runner as runner
from tools.regression import benchmark_runner
from tools.regression import screenshot_compare


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "telemetry.jsonl"
MANIFEST = ROOT / "tests" / "reference_demos" / "manifest.json"
TIMEDEMO = ROOT / "tests" / "fixtures" / "timedemo.txt"


class DemoRegressionRunnerTests(unittest.TestCase):
    def test_fixture_is_valid(self):
        frames = runner.read_telemetry(FIXTURE)
        self.assertEqual(1, len(frames))
        self.assertEqual([1.0, 2.0, 3.0], frames[0]["origin"])

    def test_capture_then_compare(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = pathlib.Path(directory) / "baseline.json"
            runner.write_baseline(baseline, "fixture", FIXTURE)
            runner.compare_baseline(baseline, "fixture", FIXTURE, 0.001)
            data = json.loads(baseline.read_text(encoding="utf-8"))
            self.assertEqual(1, data["demos"]["fixture"]["frame_count"])

    def test_detects_divergence(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = pathlib.Path(directory)
            baseline = directory_path / "baseline.json"
            changed = directory_path / "changed.jsonl"
            runner.write_baseline(baseline, "fixture", FIXTURE)
            changed.write_text(
                FIXTURE.read_text(encoding="utf-8").replace(
                    '"origin":[1.0,2.0,3.0]', '"origin":[2.0,2.0,3.0]'
                ),
                encoding="utf-8",
            )
            with self.assertRaises(runner.RegressionError):
                runner.compare_baseline(baseline, "fixture", changed, 0.001)

    def test_placeholder_manifest_is_structurally_valid(self):
        runner.verify_manifest(MANIFEST, require_files=False)

    def test_timedemo_parser(self):
        report = benchmark_runner.parse_timedemo(TIMEDEMO.read_text(encoding="utf-8"))
        self.assertEqual(120.0, report["fps"]["average"])
        self.assertEqual(12.5, report["frametime_ms"]["worst"])

    def test_benchmark_threshold(self):
        baseline = {"schema": 1, "fps": {"average": 120.0}}
        passing = {"schema": 1, "fps": {"average": 108.0}}
        failing = {"schema": 1, "fps": {"average": 100.0}}
        benchmark_runner.compare_reports(baseline, passing, 0.10, 0.15)
        with self.assertRaises(benchmark_runner.BenchmarkError):
            benchmark_runner.compare_reports(baseline, failing, 0.10, 0.15)

    def test_tga_screenshot_comparison(self):
        def write_tga(path, rgb):
            header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 1, 1, 24, 0x20)
            r, g, b = rgb
            path.write_bytes(header + bytes((b, g, r)))

        with tempfile.TemporaryDirectory() as directory:
            directory_path = pathlib.Path(directory)
            reference = directory_path / "reference.tga"
            candidate = directory_path / "candidate.tga"
            write_tga(reference, (100, 100, 100))
            write_tga(candidate, (101, 100, 100))
            report = screenshot_compare.compare_images(reference, candidate)
            self.assertLess(report["mean_absolute_difference"], 0.01)


if __name__ == "__main__":
    unittest.main()
