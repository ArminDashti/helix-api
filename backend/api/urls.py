from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("agents/", views.agents_list, name="agents-list"),
    path("agents/<str:agent_id>/instruction/", views.agent_instruction, name="agent-instruction"),
    path("agents/<str:agent_id>/", views.agent_rename, name="agent-rename"),
    path("references/", views.references_collection, name="references"),
    path("references/<str:name>/", views.reference_detail, name="reference-detail"),
    path("rules/", views.rules_collection, name="rules"),
    path("rules/assignments/", views.rules_assignments, name="rules-assignments"),
    path("rules/<str:rule_id>/rename/", views.rule_rename, name="rule-rename"),
    path("rules/<str:rule_id>/", views.rule_detail, name="rule-detail"),
    path("skills/", views.skills_collection, name="skills"),
    path("skills/<str:scope>/<str:skill_id>/rename/", views.skill_rename, name="skill-rename"),
    path("skills/<str:scope>/<str:skill_id>/", views.skill_detail, name="skill-detail"),
    path("docs/tables/", views.docs_tables, name="docs-tables"),
    path("docs/tables/<str:table>/", views.docs_table_detail, name="docs-table-detail"),
    path("results/", views.results_collection, name="results-collection"),
    path("results/<str:result_id>/", views.results_detail, name="results-detail"),
    path("db-explorer/tables/", views.db_explorer_tables, name="db-explorer-tables"),
    path("db-explorer/columns/", views.db_explorer_columns, name="db-explorer-columns"),
    path("db-explorer/query/", views.db_explorer_query, name="db-explorer-query"),
    path("admin/database/", views.admin_database, name="admin-database"),
    path("admin/provider/", views.admin_provider, name="admin-provider"),
    path("admin/openrouter/", views.admin_openrouter, name="admin-openrouter"),
    path(
        "admin/openrouter/models/",
        views.admin_openrouter_models,
        name="admin-openrouter-models",
    ),
    path("admin/cursor/", views.admin_cursor, name="admin-cursor"),
    path(
        "admin/cursor/models/",
        views.admin_cursor_models,
        name="admin-cursor-models",
    ),
    path("admin/pipeline-graph/", views.admin_pipeline_graph, name="admin-pipeline-graph"),
    path("runs/stream", views.runs_stream, name="runs-stream"),
    path("chat", views.chat, name="chat"),
]
