import os
import tempfile
import unittest
from pathlib import Path

from scripts.offline_builtin_dataset import (
    OfflineBuiltinDatasetMissingFiles,
    offline_enabled,
    verify_local_dataset_files,
)


class OfflineBuiltinDatasetTest(unittest.TestCase):
    def test_offline_enabled_only_accepts_explicit_truthy_values(self):
        old_value = os.environ.get("VDB_OFFLINE")
        try:
            for value in (None, "", "false", "False", "0", "no"):
                if value is None:
                    os.environ.pop("VDB_OFFLINE", None)
                else:
                    os.environ["VDB_OFFLINE"] = value
                self.assertFalse(offline_enabled())

            for value in ("true", "True", "1", "yes", "on"):
                os.environ["VDB_OFFLINE"] = value
                self.assertTrue(offline_enabled())
        finally:
            if old_value is None:
                os.environ.pop("VDB_OFFLINE", None)
            else:
                os.environ["VDB_OFFLINE"] = old_value

    def test_verify_local_dataset_files_passes_when_all_files_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "openai" / "openai_medium_500k"
            root.mkdir(parents=True)
            for name in ("train.parquet", "test.parquet", "neighbors.parquet"):
                root.joinpath(name).write_bytes(b"present")

            verify_local_dataset_files(
                dataset_identifier="OpenAIMedium",
                dataset_dir_name="openai_medium_500k",
                files=["train.parquet", "test.parquet", "neighbors.parquet"],
                local_ds_root=root,
            )

    def test_verify_local_dataset_files_reports_missing_files_and_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "openai" / "openai_medium_500k"
            root.mkdir(parents=True)
            root.joinpath("train.parquet").write_bytes(b"present")

            with self.assertRaises(OfflineBuiltinDatasetMissingFiles) as raised:
                verify_local_dataset_files(
                    dataset_identifier="OpenAIMedium",
                    dataset_dir_name="openai_medium_500k",
                    files=["train.parquet", "test.parquet", "neighbors.parquet"],
                    local_ds_root=root,
                )

            message = str(raised.exception)
            self.assertIn("OpenAIMedium", message)
            self.assertIn(str(root), message)
            self.assertIn("test.parquet", message)
            self.assertIn("neighbors.parquet", message)


if __name__ == "__main__":
    unittest.main()
