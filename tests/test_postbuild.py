import unittest

from ghost_builder.ui_result import format_bytes, result_summary


class PostBuildResultTests(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(5 * 1024 * 1024), "5.00 MB")

    def test_result_summary_preserves_verified_metadata(self):
        item = {
            "artifact": r"C:\\Builds\\Demo-release-v2.0.aab",
            "app_name": "Demo",
            "version_name": "2.0",
            "format": "AAB",
            "mode": "Release",
            "signed": True,
            "size_bytes": 2097152,
            "duration_seconds": 4.256,
            "sha256": "a" * 64,
        }
        summary = result_summary(item)
        self.assertEqual(summary["app"], "Demo")
        self.assertEqual(summary["format"], "AAB")
        self.assertEqual(summary["mode"], "Release")
        self.assertEqual(summary["size"], "2.00 MB")
        self.assertEqual(summary["duration"], "4.26 s")
        self.assertEqual(summary["sha256"], "a" * 64)
        self.assertEqual(summary["signed"], "yes")


if __name__ == "__main__":
    unittest.main()
