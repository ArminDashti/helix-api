import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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


class FourAgentPipelineTests(SimpleTestCase):
    def test_default_flow_uses_four_agents(self):
        from .pipeline_graph import compile_pipeline_flow, default_pipeline_flow

        graph = compile_pipeline_flow(default_pipeline_flow())
        self.assertEqual(graph["entry"], "guardian")
        self.assertEqual({node["id"] for node in graph["nodes"]}, set(AGENT_IDS))

    def test_guardian_blocks_write_prompt(self):
        from .pipeline_run import _guardian_hard_block

        blocked = _guardian_hard_block(
            "DROP TABLE Sales.Moshtary",
            {"username": "armin", "is_admin": True},
        )
        self.assertIsNotNone(blocked)

    def test_guardian_allows_grid_ask(self):
        from .pipeline_run import _guardian_hard_block

        self.assertIsNone(
            _guardian_hard_block(
                "Show top selling products as a grid",
                {"username": "guest", "is_admin": False, "is_guest": True},
            )
        )


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


class SqlExecuteTests(SimpleTestCase):
    def test_ensure_sqlserver_top_inserts_top_on_plain_select(self):
        from .sql_execute import _ensure_sqlserver_top

        self.assertEqual(
            _ensure_sqlserver_top("SELECT a FROM Sales.Moshtary", 100),
            "SELECT TOP (100) a FROM Sales.Moshtary",
        )

    def test_ensure_sqlserver_top_skips_when_top_present(self):
        from .sql_execute import _ensure_sqlserver_top

        sql = "SELECT TOP 5 a FROM Sales.Moshtary"
        self.assertEqual(_ensure_sqlserver_top(sql, 100), sql)

    def test_execute_select_uses_fetchmany_and_retries_link_failure(self):
        from .sql_execute import execute_select

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cur.description = [("a",)]
        mock_cur.fetchmany.return_value = [(1,)]
        mock_cur.execute.side_effect = [
            Exception(
                "('08S01', '[08S01] Communication link failure (SQLEndTran(SQL_ROLLBACK))')"
            ),
            None,
        ]

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config(
                    {
                        "database": {
                            "engine": "sqlserver",
                            "host": "db.internal",
                            "port": 1433,
                            "name": "Sales",
                            "user": "u",
                            "password": "p",
                        },
                        "sql": {
                            "require_row_limit": False,
                            "max_rows": 10,
                            "max_retries": 2,
                            "forbid_select_star": True,
                            "enforce_allowlist": False,
                        },
                    }
                )
                with patch("api.sql_execute.connect", return_value=mock_conn):
                    result = execute_select("SELECT a FROM Sales.Moshtary")

        self.assertEqual(result["rows"], [{"a": 1}])
        mock_cur.fetchmany.assert_called_with(10)
        mock_cur.fetchall.assert_not_called()
        self.assertEqual(mock_cur.execute.call_count, 2)

    def test_execute_select_retries_pyodbc_exception_set(self):
        from .sql_execute import execute_select

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cur.description = [("a",)]
        mock_cur.fetchmany.return_value = [(1,)]
        mock_cur.execute.side_effect = [
            SystemError(
                "<class 'pyodbc.Error'> returned a result with an exception set"
            ),
            None,
        ]

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config(
                    {
                        "database": {
                            "engine": "sqlserver",
                            "host": "db.internal",
                            "port": 1433,
                            "name": "Sales",
                            "user": "u",
                            "password": "p",
                        },
                        "sql": {
                            "require_row_limit": False,
                            "max_rows": 10,
                            "max_retries": 2,
                            "forbid_select_star": True,
                            "enforce_allowlist": False,
                        },
                    }
                )
                with patch("api.sql_execute.connect", return_value=mock_conn):
                    result = execute_select("SELECT a FROM Sales.Moshtary")

        self.assertEqual(result["rows"], [{"a": 1}])
        self.assertEqual(mock_cur.execute.call_count, 2)

    def test_sqlserver_connection_close_does_not_raise(self):
        from .db_dialects.sqlserver import _SqlServerConnection

        inner = MagicMock()
        inner.close.side_effect = SystemError(
            "<class 'pyodbc.Error'> returned a result with an exception set"
        )
        wrapper = _SqlServerConnection(inner)
        with wrapper as conn:
            self.assertIs(conn, inner)
        inner.close.assert_called_once()

    def test_sqlserver_connection_skips_close_when_query_failed(self):
        from .db_dialects.sqlserver import _SqlServerConnection

        inner = MagicMock()
        wrapper = _SqlServerConnection(inner)
        with self.assertRaises(RuntimeError):
            with wrapper:
                raise RuntimeError("query failed")
        inner.close.assert_not_called()

    def test_execute_select_exhausted_systemerror_is_friendly(self):
        from .sql_execute import execute_select

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cur.execute.side_effect = SystemError(
            "<class 'pyodbc.Error'> returned a result with an exception set"
        )

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config(
                    {
                        "database": {
                            "engine": "sqlserver",
                            "host": "db.internal",
                            "port": 1433,
                            "name": "Sales",
                            "user": "u",
                            "password": "p",
                        },
                        "sql": {
                            "require_row_limit": False,
                            "max_rows": 10,
                            "max_retries": 1,
                            "forbid_select_star": True,
                            "enforce_allowlist": False,
                        },
                    }
                )
                with patch("api.sql_execute.connect", return_value=mock_conn):
                    with self.assertRaises(ValueError) as raised:
                        execute_select("SELECT a FROM Sales.Moshtary")

        self.assertIn("SQL Server closed the connection", str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)
        self.assertNotIn("exception set", str(raised.exception).lower())

