from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path, include
from . import views


urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="token_obtain_pair"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("auth/me/", views.MeView.as_view(), name = "me"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("users/", views.ListUsersView.as_view(), name="user_list"),
    path("users/<int:pk>/", views.RetrieveUserView.as_view(), name="user_detail"),
    path("users/create/", views.CreateUserView.as_view(), name="user_create"),
    path("users/<int:pk>/update/", views.UpdateUserView.as_view(), name="user_update"),
]