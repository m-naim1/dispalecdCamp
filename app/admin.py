from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin import CustomView
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import LoginFailed

from app.core.security import get_password_hash, verify_password
from app.models.family import Family, Member
from app.models.lookups import ShelterBlock, ShelterCenter
from app.models.user import User
from app.models.enums import UserRole


class AdminAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        db: Session = request.state.session
        user = db.query(User).filter(User.username == username).first()

        if not user or not user.is_active:
            raise LoginFailed("Invalid username or password")
        if not verify_password(password, user.hashed_password):
            raise LoginFailed("Invalid username or password")
        if user.role not in (UserRole.SUPERADMIN, UserRole.MANAGER):
            raise LoginFailed("You do not have permission to access the admin panel")

        request.session.update({"admin_username": username})
        return response

    async def is_authenticated(self, request: Request) -> bool:
        username = request.session.get("admin_username")
        if not username:
            return False
        db: Session = request.state.session
        user = (
            db.query(User)
            .filter(
                User.username == username,
                User.is_active == True,
            )
            .first()
        )
        return user is not None

    async def get_admin_user(self, request: Request) -> AdminUser:
        username = request.session.get("admin_username")
        db: Session = request.state.session
        user = db.query(User).filter(User.username == username).first()
        return AdminUser(username=user.full_name or user.username)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


class DashboardView(CustomView):
    async def render(self, request: Request, templates) -> Response:
        db: Session = request.state.session

        total_families = db.query(func.count(Family.id)).scalar() or 0
        active_families = (
            db.query(func.count(Family.id)).filter(Family.is_active == True).scalar()
            or 0
        )
        total_members = db.query(func.count(Member.id)).scalar() or 0

        block_counts = (
            db.query(ShelterBlock.name_en, func.count(Family.id).label("cnt"))
            .outerjoin(Family, Family.shelter_block_id == ShelterBlock.id)
            .group_by(ShelterBlock.id)
            .order_by(func.count(Family.id).desc())
            .all()
        )

        center_counts = (
            db.query(ShelterCenter.name_en, func.count(Family.id).label("cnt"))
            .outerjoin(Family, Family.current_shelter_center_id == ShelterCenter.id)
            .group_by(ShelterCenter.id)
            .order_by(func.count(Family.id).desc())
            .all()
        )

        stats = {
            "total_families": total_families,
            "active_families": active_families,
            "archived_families": total_families - active_families,
            "total_members": total_members,
            "avg_per_family": round(total_members / total_families, 1)
            if total_families
            else 0,
            "disabled": db.query(func.count(Member.id))
            .filter(Member.disabled == True)
            .scalar()
            or 0,
            "injured": db.query(func.count(Member.id))
            .filter(Member.injured == True)
            .scalar()
            or 0,
            "pregnant": db.query(func.count(Member.id))
            .filter(Member.pregnant == True)
            .scalar()
            or 0,
            "chronic": db.query(func.count(Member.id))
            .filter(Member.has_chronic_disease == True)
            .scalar()
            or 0,
            "block_counts": block_counts,
            "center_counts": center_counts,
            "max_block": max((c for _, c in block_counts), default=1) or 1,
        }

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
            obj.hashed_password = get_password_hash(plain)

    async def before_edit(self, request, data, obj):
        plain = data.pop("hashed_password", None)
        if plain and plain.strip():
            obj.hashed_password = get_password_hash(plain)
