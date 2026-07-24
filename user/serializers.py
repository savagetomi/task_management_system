from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Read/list serializer. Never exposes the password.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "department",
            "reports_to",
            "is_active",
            "must_change_password",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "must_change_password"]

    def validate(self, attrs):
        # FR-4a enforcement on updates too, not just creation. Build a
        # candidate instance merging existing values with the incoming
        # partial-update fields, so a PATCH that only sends `department`
        # (leaving reports_to unchanged) is still checked against the
        # combination that will actually be saved.
        instance = self.instance
        department = attrs.get("department", instance.department if instance else None)
        reports_to = attrs.get("reports_to", instance.reports_to if instance else None)

        candidate = User(
            pk=instance.pk if instance else None,
            department=department,
            reports_to=reports_to,
        )
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Admin-only user creation (PRD FR-2). A secure temporary password is
    auto-generated server-side — it is never supplied by the Admin or the
    new user at this stage (FR-2a). The generated password is returned
    exactly once, in this response, so the Admin can relay it (e.g. via
    the delivery mechanism your org chooses — email is assumed at the PRD
    level, but this serializer stays transport-agnostic).
    """

    generated_password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "department",
            "reports_to",
            "generated_password",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        # Reuse User.clean() for the reports_to / department alignment rule
        # (FR-4a) so the rule lives in one place.
        instance = User(**{k: v for k, v in attrs.items() if k != "generated_password"})
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs

    def create(self, validated_data):
        user, raw_password = User.objects.create_staff_user(**validated_data)
        # Stashed on the instance only for serialization in this response;
        # never stored or logged in plaintext.
        user.generated_password = raw_password
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    PRD FR-2a / API: POST /api/auth/change-password/
    Authenticated user sets their own password, clearing
    must_change_password once done.
    """

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends simplejwt's default serializer so the login response includes
    the fields the frontend needs immediately (role, department,
    must_change_password) without a follow-up "who am I" call. See PRD
    FR-1 (JWT auth) and FR-2a (forced password change flow).
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "department": user.department_id,
            "must_change_password": user.must_change_password,
        }
        return data