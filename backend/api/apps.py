from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self) -> None:
        # Seed markdown-files from analytics/agents on first boot.
        from . import markdown_store

        markdown_store.seed_if_empty()
        markdown_store.seed_skills_if_empty()
