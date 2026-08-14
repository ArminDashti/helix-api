from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self) -> None:
        # Seed markdown-files from analytics/agents on first boot.
        from . import markdown_store
        from .sample_database import ensure_configured_sample_if_needed

        markdown_store.seed_if_empty()
        markdown_store.migrate_rule_ids()
        markdown_store.seed_skills_if_empty()
        markdown_store.ensure_skill_display_names()
        # Default analytics DB is a non-empty sample SQLite for review/testing.
        ensure_configured_sample_if_needed()
