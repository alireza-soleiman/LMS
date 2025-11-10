from django.urls import path
from . import views
from .views import ranking_page_view, save_swot_entry, swot_analysis_view

urlpatterns = [
    path('', views.workshop_list, name='workshop_list'),
    path('project/<int:project_id>/stakeholders/', views.stakeholder_list, name='stakeholder_list'),
    path('project/<int:project_id>/stakeholders/download/', views.download_stakeholders_csv,
         name='download_stakeholders'),
    path('project/<int:project_id>/stakeholders/data/', views.stakeholder_data, name='stakeholder_data_api'),
    path('project/<int:project_id>/problem-tree/', views.problem_tree_view, name='problem_tree'),
    path('stakeholder/update/<int:stakeholder_id>/', views.update_stakeholder_details, name='update_stakeholder_details'),
    path('problem/delete/<int:problem_id>/', views.delete_problem, name='delete_problem'),
    path('api/project/<int:project_id>/problem-data/', views.problem_tree_data, name='problem_tree_data_api'),
    path('stakeholder/delete/<int:stakeholder_id>/', views.delete_stakeholder, name='delete_stakeholder'),
    path('project/<int:project_id>/indicators/', views.indicator_selection_view, name='indicator_selection'),
    path('project/<int:project_id>/indicators/ranking/', views.indicator_ranking_view, name='indicator_ranking'),
    path('project/<int:project_id>/indicators/download/', views.download_indicators_csv, name='download_indicators_csv'),
    path('project/<int:project_id>/indicators/', views.indicator_selection_view, name='indicator_selection'),
    path('project/<int:project_id>/indicators/ranking/', views.indicator_ranking_view, name='indicator_ranking'),
    path('project/<int:project_id>/indicators/download/', views.download_indicators_csv, name='download_indicators_csv'),
    path('indicator/toggle/<int:indicator_id>/', views.toggle_indicator_accept, name='toggle_indicator_accept'),
    path("project/<int:project_id>/indicators/save/", views.save_indicator_selections, name="save_indicator_selections"),
    path('project/<int:project_id>/ranking/', views.ranking_page_view, name='indicator_ranking'),
    path('project/<int:project_id>/ranking/save/', views.indicator_ranking_view, name='indicator_ranking_view'),
    path('project/<int:project_id>/ranking/download/', views.download_indicators_csv, name='download_indicators_csv'),
    path('project/<int:project_id>/swot/', swot_analysis_view, name='swot_analysis'),
    path('project/<int:project_id>/swot/save/', save_swot_entry, name='save_swot_entry'),
    path('project/create/', views.create_project_view, name='create_project'),
    path('project/<int:project_id>/overview/', views.project_overview_view, name='project_overview'),

]
