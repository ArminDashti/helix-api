import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .agents import AGENT_IDS
from .config_loader import (
    _finalize_database,
    delete_custom_agent,
    get_all_agent_metas,
    get_llm_base_url,
    get_openrouter_settings,
    get_provider,
    restore_seed_pipeline_agents,
    save_config,
    update_openrouter_settings,
    update_provider,
)


class WarehouseSettingsTests(SimpleTestCase):
    def test_sqlserver_settings_are_not_replaced_with_sqlite_sample(self):
        result = _finalize_database(
            {
                "engine": "sqlserver",
                "host": "db.internal",
                "port": 1433,
                "name": "Sales",
                "user": "sa",
                "password": "secret",
            }
        )
        self.assertEqual(result["engine"], "sqlserver")
        self.assertEqual(result["host"], "db.internal")
        self.assertEqual(result["name"], "Sales")

    def test_sqlserver_clears_leftover_sample_filename(self):
        result = _finalize_database(
            {
                "engine": "sqlserver",
                "host": "db.internal",
                "name": "helix-sample.sqlite",
            }
        )
        self.assertEqual(result["engine"], "sqlserver")
        self.assertEqual(result["name"], "")


class PipelineAgentTests(SimpleTestCase):
    def test_seed_pipeline_agents_are_listed_and_deletable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config({"pipeline_agents_restored": False, "deleted_agents": list(AGENT_IDS)})
                restore_seed_pipeline_agents()
                ids = {meta["id"] for meta in get_all_agent_metas()}
                self.assertTrue(set(AGENT_IDS).issubset(ids))
                victim = AGENT_IDS[0]
                delete_custom_agent(victim)
                ids_after = {meta["id"] for meta in get_all_agent_metas()}
                self.assertNotIn(victim, ids_after)


class LlmSettingsTests(SimpleTestCase):
    def test_leftover_cursor_provider_reads_as_openrouter(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config({"provider": "cursor"})
                self.assertEqual(get_provider(), "openrouter")

    def test_openai_compatible_requires_stored_base_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config({"provider": "openai_compatible", "openrouter": {}})
                self.assertEqual(get_provider(), "openai_compatible")
                self.assertEqual(get_llm_base_url(), "")
                self.assertEqual(get_openrouter_settings()["base_url"], "")

    def test_openrouter_defaults_base_url_and_saves_custom(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config({"provider": "openrouter"})
                self.assertEqual(
                    get_llm_base_url(), "https://openrouter.ai/api/v1"
                )
                update_provider("openai_compatible")
                update_openrouter_settings(
                    {"base_url": "https://api.openai.com/v1/"}
                )
                self.assertEqual(get_provider(), "openai_compatible")
                self.assertEqual(get_llm_base_url(), "https://api.openai.com/v1")

    def test_host_docker_internal_falls_back_when_unresolvable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config(
                    {
                        "provider": "openai_compatible",
                        "openrouter": {
                            "base_url": "http://host.docker.internal:8140/v1"
                        },
                    }
                )
                with patch(
                    "api.config_loader.socket.getaddrinfo",
                    side_effect=OSError(11001, "getaddrinfo failed"),
                ):
                    self.assertEqual(
                        get_llm_base_url(), "http://127.0.0.1:8140/v1"
                    )

