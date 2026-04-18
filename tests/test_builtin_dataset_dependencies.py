import unittest
from unittest.mock import patch

from scripts.builtin_dataset_dependencies import (
    BuiltinDatasetDependencyError,
    ensure_builtin_dataset_dependencies,
)


class BuiltinDatasetDependenciesTest(unittest.TestCase):
    def test_reports_builtin_dataset_install_command_for_missing_dependency(self):
        def fake_find_spec(name):
            if name == "_cffi_backend":
                return None
            return object()

        with patch("importlib.util.find_spec", side_effect=fake_find_spec):
            with self.assertRaises(BuiltinDatasetDependencyError) as ctx:
                ensure_builtin_dataset_dependencies()

        message = str(ctx.exception)
        self.assertIn("_cffi_backend", message)
        self.assertIn("pip install -r requirements.txt", message)
        self.assertIn("cffi", message)


if __name__ == "__main__":
    unittest.main()
