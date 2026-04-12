from starlette_admin.contrib.sqla import ModelView
from app.core.security import get_password_hash


class UserAdminView(ModelView):
    """
    Custom admin view for User that hashes the password
    before saving, so the admin types a plain password.
    """

    # Show a plain-text password field instead of hashed_password
    exclude_fields_from_list = ["hashed_password"]
    exclude_fields_from_detail = ["hashed_password"]

    # Override the fields shown in the create/edit form
    form_include_pk = False

    async def before_create(self, request, data, obj):
        """Hash the password before creating a new user."""
        plain = data.pop("hashed_password", None)
        if plain:
            obj.hashed_password = get_password_hash(plain)

    async def before_edit(self, request, data, obj):
        """Only hash if admin typed a new password; leave unchanged if blank."""
        plain = data.pop("hashed_password", None)
        if plain and plain.strip():
            obj.hashed_password = get_password_hash(plain)
        # If blank, do nothing — keep the existing hash
