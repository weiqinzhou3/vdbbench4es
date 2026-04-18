import os
import unittest
from unittest.mock import patch

from scripts.es_connection_options import (
    build_elasticsearch_options,
    configure_insecure_request_warning,
)


class ElasticsearchOptionsTest(unittest.TestCase):
    def test_verify_certs_true_keeps_ssl_warnings_enabled_by_default(self):
        env = {
            "ES_HOSTS": "https://es.example:9200",
            "ES_USER": "elastic",
            "ES_PASSWORD": "secret",
            "ES_VERIFY_CERTS": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            options = build_elasticsearch_options()

        self.assertEqual(options["hosts"], ["https://es.example:9200"])
        self.assertTrue(options["verify_certs"])
        self.assertTrue(options["ssl_show_warn"])
        self.assertEqual(options["basic_auth"], ("elastic", "secret"))

    def test_verify_certs_false_suppresses_ssl_warnings_by_default(self):
        env = {
            "ES_HOSTS": "https://es.example:9200",
            "ES_VERIFY_CERTS": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            options = build_elasticsearch_options()

        self.assertFalse(options["verify_certs"])
        self.assertFalse(options["ssl_show_warn"])

    def test_explicit_ssl_show_warn_overrides_default(self):
        env = {
            "ES_VERIFY_CERTS": "false",
            "ES_SSL_SHOW_WARN": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            options = build_elasticsearch_options()

        self.assertFalse(options["verify_certs"])
        self.assertTrue(options["ssl_show_warn"])

    def test_legacy_suppress_env_is_supported(self):
        env = {
            "ES_VERIFY_CERTS": "false",
            "ES_SUPPRESS_INSECURE_WARNING": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            options = build_elasticsearch_options()

        self.assertFalse(options["verify_certs"])
        self.assertFalse(options["ssl_show_warn"])

    def test_configures_urllib3_warning_filter_only_for_insecure_suppressed_mode(self):
        with patch("urllib3.disable_warnings") as disable_warnings:
            configure_insecure_request_warning(verify_certs=False, ssl_show_warn=False)

        disable_warnings.assert_called_once()

        with patch("urllib3.disable_warnings") as disable_warnings:
            configure_insecure_request_warning(verify_certs=True, ssl_show_warn=False)

        disable_warnings.assert_not_called()


if __name__ == "__main__":
    unittest.main()
