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


class SixAgentPipelineTests(SimpleTestCase):
    def test_default_flow_uses_six_steps(self):
        from .pipeline_graph import compile_pipeline_flow, default_pipeline_flow

        graph = compile_pipeline_flow(default_pipeline_flow())
        self.assertEqual(graph["entry"], "guardian")
        node_ids = [node["id"] for node in graph["nodes"]]
        self.assertEqual(len(node_ids), 6)
        self.assertIn("validator__2", node_ids)
        self.assertIn("publisher", node_ids)

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

    def test_data_gatherer_sql_error_returns_failed_not_raise(self):
        from . import markdown_store as store
        from .pipeline_run import _run_agent

        ctx = {
            "prompt": "top products",
            "mode": "grid",
            "language": "en",
            "actor": {"username": "armin", "is_admin": True},
            "artifacts": {},
        }
        with patch("api.pipeline_run.complete_chat") as chat:
            chat.return_value = '{"result":"done","sql":"SELECT 1","message":"ok"}'
            with patch("api.pipeline_run.execute_select") as exe:
                exe.side_effect = ValueError("Invalid object name")
                with patch.object(store, "assemble_agent_prompt", return_value="system"):
                    status, message = _run_agent("data-gatherer", ctx)
        self.assertEqual(status, "failed")
        self.assertIn("Invalid object name", message)

    def test_jalali_tir_1405_gregorian_bounds(self):
        from .jalali_dates import calendar_hint_for_prompt, jalali_to_gregorian

        gy, gm, gd = jalali_to_gregorian(1405, 4, 1)
        self.assertEqual((gy, gm, gd), (2026, 6, 22))
        hint = calendar_hint_for_prompt(
            "میزان فروش پر فروش ترین کالای مرکز کرمان در تیر 1405"
        )
        self.assertIn("Sal = 1405", hint)
        self.assertIn("TarikhFaktor >= '2026-06-22'", hint)
        self.assertIn("TarikhFaktor < '2026-07-23'", hint)
        self.assertIn("YEAR(TarikhFaktor) = 1405", hint)
        self.assertIn("N'کرمان'", hint)

    def test_data_gatherer_prompt_includes_calendar_hint(self):
        from . import markdown_store as store
        from .pipeline_run import _run_agent

        ctx = {
            "prompt": "تیر 1405 کرمان",
            "mode": "grid",
            "language": "fa",
            "actor": {"username": "armin", "is_admin": True},
            "artifacts": {},
        }
        with patch("api.pipeline_run.complete_chat") as chat:
            chat.return_value = '{"result":"done","sql":"SELECT TOP 1 1 AS n","message":"ok"}'
            with patch("api.pipeline_run.execute_select") as exe:
                exe.return_value = {"sql": "SELECT TOP 1 1 AS n", "columns": ["n"], "rows": [{"n": 1}]}
                with patch.object(store, "assemble_agent_prompt", return_value="system"):
                    status, _message = _run_agent("data-gatherer", ctx)
        self.assertEqual(status, "done")
        user = chat.call_args[0][1]
        self.assertIn("TarikhFaktor >= '2026-06-22'", user)

    def test_first_validator_fail_edge_targets_data_gatherer(self):
        from .pipeline_graph import compile_pipeline_flow, default_pipeline_flow, next_edge

        graph = compile_pipeline_flow(default_pipeline_flow())
        edge = next_edge(graph, "validator", "fail", {})
        self.assertIsNotNone(edge)
        self.assertEqual(edge["target"], "data-gatherer")

    def test_second_validator_fail_edge_targets_result_builder(self):
        from .pipeline_graph import compile_pipeline_flow, default_pipeline_flow, next_edge

        graph = compile_pipeline_flow(default_pipeline_flow())
        edge = next_edge(graph, "validator__2", "fail", {})
        self.assertIsNotNone(edge)
        self.assertEqual(edge["target"], "result-builder")

    def test_prepare_data_gatherer_retry_resets_validator_state(self):
        from .pipeline_run import _prepare_data_gatherer_retry

        ctx = {
            "validator_visit": 1,
            "sql_fetch": {"sql": "SELECT 1", "rows": []},
            "last_error": "wrong table",
        }
        _prepare_data_gatherer_retry(ctx)
        self.assertEqual(ctx["validator_visit"], 0)
        self.assertNotIn("sql_fetch", ctx)

    def test_validator_after_retry_uses_first_visit_prompt(self):
        from . import markdown_store as store
        from .pipeline_run import _prepare_data_gatherer_retry, _run_agent

        ctx = {
            "prompt": "top products",
            "mode": "grid",
            "language": "en",
            "actor": {"username": "armin", "is_admin": True},
            "artifacts": {"validator": {"message": "wrong grain"}},
            "validator_visit": 1,
            "last_error": "wrong grain",
        }
        _prepare_data_gatherer_retry(ctx)
        captured: list[str] = []

        def fake_chat(agent_id, user, system):
            captured.append(user)
            return '{"result":"pass","message":"ok"}'

        with patch("api.pipeline_run.complete_chat", side_effect=fake_chat):
            with patch.object(store, "assemble_agent_prompt", return_value="system"):
                status, _ = _run_agent("validator", ctx)
        self.assertEqual(status, "pass")
        self.assertEqual(ctx["validator_visit"], 1)
        self.assertTrue(captured)
        self.assertIn("first validator visit", captured[0].lower())
        self.assertNotIn("second validator visit", captured[0].lower())

    def test_assemble_prompt_includes_references_section(self):
        from . import markdown_store as store

        with patch.object(store, "list_references") as refs:
            refs.return_value = [
                {"name": "tables", "content": "# tables"},
                {"name": "base-instruction", "content": "# base"},
            ]
            with patch("api.db_dialects.list_tables", return_value=[{"schema": "Sales", "name": "Moshtary", "full_name": "Sales.Moshtary"}]):
                with patch.object(store, "list_rules", return_value=[]):
                    with patch.object(store, "list_skills", return_value=[]):
                        with patch(
                            "api.docs_catalog.format_live_catalog_for_prompt",
                            return_value="### Sales.Moshtary\nColumns: ccMoshtary, NameMoshtary",
                        ):
                            prompt = store.assemble_agent_prompt("guardian")
        self.assertIn("## References", prompt)
        self.assertIn("base-instruction", prompt)
        self.assertIn("## Live catalog", prompt)
        self.assertIn("NameMoshtary", prompt)


class DocsCatalogPromptTests(SimpleTestCase):
    def test_filter_tables_reference_keeps_matching_sections_only(self):
        from .docs_catalog import filter_tables_reference

        md = (
            "# Generic\n\n"
            "## Sales.Moshtary\n\n| Column | Description |\n| ccMoshtary | id |\n\n"
            "## Missing.Table\n\n| Column | Description |\n| x | y |\n"
        )
        filtered = filter_tables_reference(md, {"Sales.Moshtary"})
        self.assertIn("Sales.Moshtary", filtered)
        self.assertNotIn("Missing.Table", filtered)

    def test_format_live_catalog_lists_columns(self):
        from . import docs_catalog

        with patch.object(
            docs_catalog.db_sql,
            "list_tables",
            return_value=[{"schema": "SalesLT", "name": "Product", "full_name": "SalesLT.Product"}],
        ):
            with patch.object(
                docs_catalog.db_sql,
                "list_columns",
                return_value=[{"name": "ProductID"}, {"name": "Name"}],
            ):
                with patch.object(docs_catalog, "_docs_markdown", return_value=""):
                    text = docs_catalog.format_live_catalog_for_prompt(max_tables=5)
        self.assertIn("SalesLT.Product", text)
        self.assertIn("ProductID", text)
        self.assertIn("Name", text)


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

    def test_unresolvable_container_hostname_falls_back_to_localhost(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "helix.config.yaml"
            with override_settings(HELIX_CONFIG_PATH=str(config_path)):
                save_config(
                    {
                        "provider": "openai_compatible",
                        "openrouter": {
                            "base_url": "http://cursor-openai-adapter-api:8140/v1"
                        },
                    }
                )
                with patch(
                    "api.config_loader.socket.getaddrinfo",
                    side_effect=OSError(11001, "getaddrinfo failed"),
                ):
                    self.assertEqual(
                        get_llm_base_url(),
                        "http://127.0.0.1:8140/v1",
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


class ResultsStoreTests(SimpleTestCase):
    def test_create_result_persists_duration_in_list_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MARKDOWN_FILES_DIR=tmp):
                from . import results_store

                item = results_store.create_result(
                    prompt="top products",
                    mode="grid",
                    language="en",
                    payload={"grid": {"columns": [], "rows": []}},
                    duration_s=12.44,
                )
                self.assertEqual(item["duration_s"], 12.44)
                listed = results_store.list_results()
                self.assertEqual(listed[0]["duration_s"], 12.44)

    def test_create_result_ignores_invalid_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MARKDOWN_FILES_DIR=tmp):
                from . import results_store

                item = results_store.create_result(
                    prompt="no duration",
                    mode="grid",
                    language="en",
                    payload={},
                    duration_s="slow",
                )
                self.assertIsNone(item["duration_s"])
                listed = results_store.list_results()
                self.assertIsNone(listed[0]["duration_s"])

