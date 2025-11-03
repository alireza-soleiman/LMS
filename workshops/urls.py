from django.urls import path
from . import views

urlpatterns = [
    path('', views.workshop_list, name='workshop_list'),
    path('project/<int:project_id>/stakeholders/', views.stakeholder_list, name='stakeholder_list'),
    path('project/<int:project_id>/stakeholders/download/', views.download_stakeholders_csv,
         name='download_stakeholders'),
    path('project/<int:project_id>/stakeholders/data/', views.stakeholder_data, name='stakeholder_data_api'),
    path('project/<int:project_id>/problem-tree/', views.problem_tree_view, name='problem_tree'),
    path('stakeholder/update/<int:stakeholder_id>/', views.update_stakeholder_details, name='update_stakeholder_details'),
    path('project/<int:project_id>/problem-tree/download/png/', views.download_problem_tree_png, name='download_problem_tree_png'),
    path('problem/delete/<int:problem_id>/', views.delete_problem, name='delete_problem'),
    path('api/project/<int:project_id>/problem-data/', views.problem_tree_data, name='problem_tree_data_api'),
    path('stakeholder/delete/<int:stakeholder_id>/', views.delete_stakeholder, name='delete_stakeholder'),
]
