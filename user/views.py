from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
)

# Shared response shape for a single user record, reused across schemas.
_USER_DATA_FIELDS = {
    "id": serializers.IntegerField(),
    "username": serializers.CharField(),
    "email": serializers.EmailField(),
    "first_name": serializers.CharField(),
    "last_name": serializers.CharField(),
    "role": serializers.CharField(),
    "department": serializers.IntegerField(allow_null=True),
    "reports_to": serializers.IntegerField(allow_null=True),
    "is_active": serializers.BooleanField(),
    "must_change_password": serializers.BooleanField(),
    "date_joined": serializers.DateTimeField(),
}


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Kept as a class subclassing simplejwt's TokenObtainPairView — there's
    no function/single-purpose equivalent provided by the library, so
    overriding the serializer here is the cleanest hook point.
    """

    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        tags=["Auth"],
        summary="Log in",
        description=(
            "Authenticates a user with username/password and returns "
            "access + refresh JWTs, plus a `user` payload (role, "
            "department, must_change_password) so the client can route a "
            "first-login user straight to a forced password-change screen."
        ),
        responses={
            200: inline_serializer(
                name="LoginResponse",
                fields={
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                    "user": inline_serializer(
                        name="LoginUserData", fields=_USER_DATA_FIELDS
                    ),
                },
            ),
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Authenticated user sets their own password (PRD FR-2a). Clears
    `must_change_password` once done.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Change my password",
        description=(
            "Sets a new password for the authenticated user, after "
            "verifying their current password. Clears `must_change_password` "
            "so the client can stop prompting for a forced change."
        ),
        request=ChangePasswordSerializer,
        responses={
            200: inline_serializer(
                name="ChangePasswordResponse",
                fields={"message": serializers.CharField()},
            ),
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """
    GET /api/auth/me/ — "who am I" convenience endpoint.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get my profile",
        description="Returns the authenticated user's own account record.",
        responses={
            200: inline_serializer(
                name="MeResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="MeData", fields=_USER_DATA_FIELDS
                    ),
                },
            ),
        },
    )
    def get(self, request):
        return Response(
            {
                "message": "User profile retrieved successfully",
                "data": UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class ListUsersView(APIView):
    """
    GET /api/users/ — list all users (admin only).
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Users"],
        operation_id="users_list",
        summary="List all users",
        description="Admin-only. Returns every user account in the system.",
        responses={
            200: inline_serializer(
                name="ListUsersResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": UserSerializer(many=True),
                },
            ),
        },
    )
    def get(self, request):
        users = User.objects.select_related("department", "reports_to").all()
        serializer = UserSerializer(users, many=True)
        return Response(
            {"message": "Users retrieved successfully", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class CreateUserView(APIView):
    """
    POST /api/users/ — create a new user account (admin only).
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Users"],
        summary="Create a new user",
        description=(
            "Admin-only. Creates a user account with a system-generated "
            "temporary password (PRD FR-2 / FR-2a) — the password is never "
            "supplied by the caller. The generated password is returned "
            "exactly once, in this response, and must be relayed to the "
            "new user; it cannot be retrieved again afterward. The account "
            "is created with `must_change_password=True`."
        ),
        request=UserCreateSerializer,
        responses={
            201: inline_serializer(
                name="CreateUserResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="CreateUserData",
                        fields={
                            "id": serializers.IntegerField(),
                            "username": serializers.CharField(),
                            "email": serializers.EmailField(),
                            "first_name": serializers.CharField(),
                            "last_name": serializers.CharField(),
                            "role": serializers.CharField(),
                            "department": serializers.IntegerField(allow_null=True),
                            "reports_to": serializers.IntegerField(allow_null=True),
                            "generated_password": serializers.CharField(),
                        },
                    ),
                },
            ),
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "User created successfully",
                    "data": UserCreateSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RetrieveUserView(APIView):
    """
    GET /api/users/<pk>/ — an admin can view anyone; a user can view
    their own record only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        operation_id="users_retrieve",
        summary="Retrieve a user",
        description="Admins can retrieve any user; other users can only retrieve themselves.",
        responses={
            200: inline_serializer(
                name="RetrieveUserResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="RetrieveUserData", fields=_USER_DATA_FIELDS
                    ),
                },
            ),
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if request.user.role != User.Role.ADMIN and request.user.id != user.id:
            raise PermissionDenied("You can only view your own profile.")
        return Response(
            {"message": "User retrieved successfully", "data": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class UpdateUserView(APIView):
    """
    PATCH /api/users/<pk>/ — admin only. Updates role/department/
    reports_to/is_active etc. No DELETE — users are never hard-deleted
    (PRD NFR-3 mirrors this for tasks too); deactivate via is_active=False.
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Users"],
        summary="Update a user",
        description=(
            "Admin-only. Partial update of a user account — role, "
            "department, reports_to, is_active, etc. Enforces FR-4a "
            "(reports_to must be in the same department, unless it's an "
            "Admin) on every update, not just creation."
        ),
        request=UserSerializer,
        responses={
            200: inline_serializer(
                name="UpdateUserResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="UpdateUserData", fields=_USER_DATA_FIELDS
                    ),
                },
            ),
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(
            user, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)