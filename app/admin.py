from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin import CustomView
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import LoginFailed

from app.core.security import get_password_hash, verify_password
from app.models.enums import UserRole
from app.repositories.userrepository import UserRepository
from app.services.family_service import get_dashboard_stats
from app.services.user_service import UserService


class AdminAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        db: AsyncSession = request.state.session

        # 1. Instantiate Repository and Service with the current request's DB session
        user_repo = UserRepository(db)
        user_service = UserService(user_repo)

        # 2. Call the service method (notice we no longer pass 'db' to the service)
        try:
            user = await user_service.get_by_username(username)
        except Exception:
            # DB outage
            raise LoginFailed("The Server is down")
        if not user:
            raise LoginFailed("Invalid username or password")

        if not await verify_password(password, user.hashed_password):
            raise LoginFailed("Invalid username or password")

        if user.role not in (UserRole.SUPERADMIN, UserRole.MANAGER):
            raise LoginFailed("You do not have permission to access the admin panel")

        request.session.update(
            {
                "admin_username": username,
                "admin_full_name": user.full_name or username,
            }
        )
        return response

    async def is_authenticated(self, request: Request) -> bool:
        username = request.session.get("admin_username")
        if not username:
            return False

        db: AsyncSession = request.state.session
        user_repo = UserRepository(db)
        user_service = UserService(user_repo)

        try:
            user = await user_service.get_active_user_by_username(str(username))
            return user is not None
        except Exception:
            # If the DB is down or query fails, don't crash the app.
            # Just treat the user as unauthenticated and redirect to login.
            return False

    def get_admin_user(self, request: Request) -> AdminUser | None:
        username = request.session.get("admin_username")
        if not username:
            return None
        # Full name may have been stored at login; fall back to username
        full_name = request.session.get("admin_full_name") or username
        return AdminUser(username=full_name)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


class DashboardView(CustomView):
    async def render(self, request: Request, templates) -> Response:
        db: AsyncSession = request.state.session

        # get_dashboard_stats remains a standalone async function that takes the db session
        stats = await get_dashboard_stats(db)

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"stats": stats},
        )


class UserAdminView(ModelView):
    exclude_fields_from_list = ["hashed_password"]
    exclude_fields_from_detail = ["hashed_password"]
    form_include_pk = False

    async def before_create(self, request, data, obj):
        plain = data.pop("hashed_password", None)
        if plain:
            obj.hashed_password = await get_password_hash(plain)

    async def before_edit(self, request, data, obj):
        plain = data.pop("hashed_password", None)
        if plain and plain.strip():
            obj.hashed_password = await get_password_hash(plain)
