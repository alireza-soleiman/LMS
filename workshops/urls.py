from django.urls import path
from . import views
from .views import ranking_page_view, save_swot_entry, swot_analysis_view

urlpatterns = [
    # Workshop List
    path("project/<int:project_id>/workshops/", views.workshop_list_view, name="workshop_list"),

    # WORKSHOP 1 — Project Overview
    path("project/<int:project_id>/workshops/overview/", views.project_overview_view, name="project_overview"),

    # WORKSHOP 2.1 — Stakeholders
    path("project/<int:project_id>/stakeholders/", views.stakeholder_list, name="stakeholder_list"),
    path("project/<int:project_id>/stakeholders/download/", views.download_stakeholders_csv, name="download_stakeholders"),
    path("project/<int:project_id>/stakeholders/data/", views.stakeholder_data, name="stakeholder_data_api"),
    path("stakeholder/update/<int:stakeholder_id>/", views.update_stakeholder_details, name="update_stakeholder_details"),
    path("stakeholder/delete/<int:stakeholder_id>/", views.delete_stakeholder, name="delete_stakeholder"),

    # WORKSHOP 2.2 — Problem Tree
    path("project/<int:project_id>/problem-tree/", views.problem_tree_view, name="problem_tree"),
    path("api/project/<int:project_id>/problem-data/", views.problem_tree_data, name="problem_tree_data_api"),
    path("problem/delete/<int:problem_id>/", views.delete_problem, name="delete_problem"),

    # WORKSHOP 2.3 — objective Tree
    # WORKSHOP 2.3 — Objective Tree
    path("project/<int:project_id>/objective-tree/", views.objective_tree_view, name="objective_tree"),
    path("project/<int:project_id>/objective-tree/data/",views.objective_tree_data,name="objective_tree_data"),
    path("objective/delete/<int:objective_id>/",views.delete_objective,name="delete_objective"),

    # WORKSHOP 3.1 — Indicator Selection
    path("project/<int:project_id>/indicators/", views.indicator_selection_view, name="indicator_selection"),
    path("project/<int:project_id>/indicators/save/", views.save_indicator_selections, name="save_indicator_selections"),
    path("indicator/toggle/<int:indicator_id>/", views.toggle_indicator_accept, name="toggle_indicator_accept"),

    # WORKSHOP 3.2 — Indicator Ranking (SRF)
    path("project/<int:project_id>/ranking/", ranking_page_view, name="indicator_ranking"),
    path("project/<int:project_id>/ranking/save/", views.indicator_ranking_view, name="indicator_ranking_view"),
    path("project/<int:project_id>/ranking/download/", views.download_indicators_csv, name="download_indicators_csv"),

    # WORKSHOP 4 — SWOT Analysis
    path("project/<int:project_id>/swot/", swot_analysis_view, name="swot_analysis"),
    path("project/<int:project_id>/swot/save/", save_swot_entry, name="save_swot_entry"),

    # Workshop 5 — Scenario Building
    path("project/<int:project_id>/scenario/", views.scenario_building_view, name="scenario_building"),
    path("project/<int:project_id>/scenario/qsort/", views.scenario_qsort_view, name="scenario_qsort"),
    path("project/<int:project_id>/scenario/results/", views.scenario_results_view, name="scenario_results"),
    path("project/<int:project_id>/scenario/save/", views.save_scenario, name="save_scenario"),

    # Project Creation
    path("project/create/", views.create_project_view, name="create_project"),


]
