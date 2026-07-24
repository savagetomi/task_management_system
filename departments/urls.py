from django.urls import path

from . import views

urlpatterns = [
    path("departments/", views.ListDepartmentsView.as_view(), name="department_list"),
    path("departments/create/", views.CreateDepartmentView.as_view(), name="department_create"),
    path("departments/<int:pk>/", views.RetrieveDepartmentView.as_view(), name="department_detail"),
    path("departments/<int:pk>/update/", views.UpdateDepartmentView.as_view(), name="department_update"),
]