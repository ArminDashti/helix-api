from django.urls import path

from . import views

urlpatterns = [
    path("agents/", views.agents_list, name="agents-list"),
    path("agents/<str:agent_id>/instruction/", views.agent_instruction, name="agent-instruction"),
    path("references/", views.references_collection, name="references"),
    path("references/<str:name>/", views.reference_detail, name="reference-detail"),
    path("rules/", views.rules_collection, name="rules"),
    path("rules/assignments/", views.rules_assignments, name="rules-assignments"),
    path("rules/<str:rule_id>/", views.rule_detail, name="rule-detail"),
    path("skills/", views.skills_collection, name="skills"),
    path("skills/<str:scope>/<str:skill_id>/", views.skill_detail, name="skill-detail"),
    path("admin/database/", views.admin_database, name="admin-database"),
    path("admin/openrouter/", views.admin_openrouter, name="admin-openrouter"),
    path("runs/stream", views.runs_stream, name="runs-stream"),
    path("chat", views.chat, name="chat"),
]
