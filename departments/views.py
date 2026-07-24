from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from user.permissions import IsAdmin

from .models import Department
from .serializers import DepartmentSerializer

_DEPARTMENT_DATA_FIELDS = {
    "id": serializers.IntegerField(),
    "name": serializers.CharField(),
    "head": serializers.IntegerField(allow_null=True),
    "is_active": serializers.BooleanField(),
    "created_at": serializers.DateTimeField(),
}


class ListDepartmentsView(APIView):
    """
    GET /api/departments/ — list all departments. Any authenticated user
    can view the department list (needed for dropdowns etc.); only Admins
    can create/update (PRD FR-5).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Departments"],
        operation_id="departments_list",
        summary="List all departments",
        responses={
            200: inline_serializer(
                name="ListDepartmentsResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": DepartmentSerializer(many=True),
                },
            ),
        },
    )
    def get(self, request):
        departments = Department.objects.select_related("head").all()
        serializer = DepartmentSerializer(departments, many=True)
        return Response(
            {"message": "Departments retrieved successfully", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class CreateDepartmentView(APIView):
    """
    POST /api/departments/create/ — admin only (PRD FR-5).
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Departments"],
        summary="Create a new department",
        description="Admin-only. `head` is optional — a brand-new department may not have a manager assigned yet (see PRD FR-4a fallback).",
        request=DepartmentSerializer,
        responses={
            201: inline_serializer(
                name="CreateDepartmentResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="CreateDepartmentData", fields=_DEPARTMENT_DATA_FIELDS
                    ),
                },
            ),
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            department = serializer.save()
            return Response(
                {
                    "message": "Department created successfully",
                    "data": DepartmentSerializer(department).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RetrieveDepartmentView(APIView):
    """
    GET /api/departments/<pk>/ — any authenticated user.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Departments"],
        operation_id="departments_retrieve",
        summary="Retrieve a department",
        responses={
            200: inline_serializer(
                name="RetrieveDepartmentResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="RetrieveDepartmentData", fields=_DEPARTMENT_DATA_FIELDS
                    ),
                },
            ),
            404: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        return Response(
            {
                "message": "Department retrieved successfully",
                "data": DepartmentSerializer(department).data,
            },
            status=status.HTTP_200_OK,
        )


class UpdateDepartmentView(APIView):
    """
    PATCH /api/departments/<pk>/update/ — admin only. Rename, reassign
    head, or deactivate (PRD FR-6/FR-7). Deactivation is blocked if the
    department still has active members. No DELETE.
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Departments"],
        summary="Update a department",
        description="Admin-only. Deactivating (is_active=False) is rejected if the department still has active members (PRD FR-7).",
        request=DepartmentSerializer,
        responses={
            200: inline_serializer(
                name="UpdateDepartmentResponse",
                fields={
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="UpdateDepartmentData", fields=_DEPARTMENT_DATA_FIELDS
                    ),
                },
            ),
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def patch(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Department updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)