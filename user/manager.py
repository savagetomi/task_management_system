from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom manager for the accounts.User model.

    Two entry points:
    - create_user / create_superuser: standard Django plumbing, needed
      because we swapped the default user model (required by Django even
      if you don't call these directly very often).
    - create_staff_user: the PRD FR-2 / FR-2a path — an Admin creating a
      new user, where the system auto-generates the password rather than
      accepting one from the caller.
    """

    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("Username is required.")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.ADMIN)
        extra_fields.setdefault("must_change_password", False)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, email, password, **extra_fields)

    def create_staff_user(self, *, username, email, role, department=None,
                           reports_to=None, first_name="", last_name=""):
        """
        PRD FR-2 / FR-2a: the Admin-driven creation path. Generates a secure
        temporary password server-side, sets must_change_password=True, and
        returns (user, raw_password) so the caller (the view) can hand the
        raw password back exactly once in the API response — it is never
        stored or logged in plaintext anywhere after this.
        """
        from .models import generate_temporary_password

        raw_password = generate_temporary_password()
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            role=role,
            department=department,
            reports_to=reports_to,
            first_name=first_name,
            last_name=last_name,
            must_change_password=True,
        )
        user.set_password(raw_password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user, raw_password