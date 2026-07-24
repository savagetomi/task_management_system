from django.conf import settings
from django.db import models


class Department(models.Model):
    """
    See PRD section 3.2, FR-5/FR-6/FR-7.
    """

    name = models.CharField(max_length=100, unique=True)

    # The manager who leads this department. Nullable because a brand-new
    # department may not have a head assigned yet (see PRD FR-4a fallback
    # scenario, where reports_to falls back to an Admin in this case).
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_department",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name