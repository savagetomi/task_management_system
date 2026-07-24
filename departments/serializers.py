from rest_framework import serializers

from .models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "head", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        # FR-7: deactivating a department is blocked if it has active users.
        instance = self.instance
        is_active = attrs.get("is_active", instance.is_active if instance else True)
        if instance and instance.is_active and not is_active:
            active_members = instance.members.filter(is_active=True).exists()
            if active_members:
                raise serializers.ValidationError(
                    {
                        "is_active": (
                            "Cannot deactivate a department with active "
                            "members. Reassign users first."
                        )
                    }
                )
        return attrs