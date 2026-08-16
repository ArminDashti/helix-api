import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from .agents import AGENT_IDS
from .config_loader import (
    _finalize_database,
    delete_custom_agent,
    get_all_agent_metas,
    restore_seed_pipeline_agents,
    save_config,
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
