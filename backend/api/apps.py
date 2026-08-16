from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self) -> None:
        # Seed markdown-files from analytics/agents on first boot.
        from . import markdown_store
        from .ensure_packages import ensure_pyodbc_installed
        from .sample_database import ensure_configured_sample_if_needed

        ensure_pyodbc_installed()

        markdown_store.seed_if_empty()
        markdown_store.migrate_rule_ids()
        markdown_store.migrate_sql_agent_id()
        markdown_store.seed_skills_if_empty()
        markdown_store.ensure_skill_display_names()
        markdown_store.ensure_default_rule_assignments()
        markdown_store.ensure_default_skill_assignments()
        from .config_loader import restore_seed_pipeline_agents
        from . import org

        restore_seed_pipeline_agents()
        org.ensure_org()
        # Default analytics DB is a non-empty sample SQLite for review/testing.
        ensure_configured_sample_if_needed()
