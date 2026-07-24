import secrets
import string

from django.contrib.auth.models import AbstractUser
from django.db import models

from .manager import UserManager


def generate_temporary_password(length: int = 12) -> str:
    """
    Generate a secure, random temporary password for newly created accounts.
    See PRD FR-2a: passwords are never chosen by the Admin or the user at
    creation time; the system generates one and the user must change it
    after their first login.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class User(AbstractUser):
    """
    Custom user model. Extends Django's AbstractUser to add role, department,
    and reporting-line fields required by the PRD's permission model.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        EMPLOYEE = "employee", "Employee"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    reports_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_reports",
    )
    # temporary password and hasn't set their own yet.
    must_change_password = models.BooleanField(default=True)

    objects = UserManager()

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.reports_to_id and self.reports_to.role != User.Role.ADMIN:
            if self.reports_to.department_id != self.department_id:
                raise ValidationError(
                    {
                        "reports_to": (
                            "reports_to must belong to the same department "
                            "as the user, unless reports_to is an Admin."
                        )
                    }
                )

        # A user shouldn't report to themselves.
        if self.reports_to_id and self.reports_to_id == self.id:
            from django.core.exceptions import ValidationError as VE

            raise VE({"reports_to": "A user cannot report to themselves."})

    @property
    def is_admin_role(self) -> bool:
        return self.role == User.Role.ADMIN

    @property
    def is_manager_role(self) -> bool:
        return self.role == User.Role.MANAGER

    @property
    def is_employee_role(self) -> bool:
        return self.role == User.Role.EMPLOYEE

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.role})"
