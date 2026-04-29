import uvicorn
from fastapi import FastAPI
from starlette_admin.contrib.sqla import Admin, ModelView
from app.admin import UserAdminView, DashboardView
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app.models.family import Family, Member
from app.models.user import User
from app.models.lookups import (
    City,
    Governor,
    RelationshipToHead,
    ShelterQuality,
    ShelterBlock,
    ShelterCenter,
)

# Import models to ensure tables are created
# from app.models import family
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.enums import UserRole

Base.metadata.create_all(bind=engine)


app = FastAPI(title=settings.PROJECT_NAME)

admin = Admin(
    engine=engine,
    title="Displaced Camp Admin",
    templates_dir="templates",  # ← tells admin where your templates folder is
    index_view=DashboardView(
        label="Dashboard",
        icon="fa fa-home",
        path="/",
        add_to_menu=False,  # already the home page, no need to show in sidebar
    ),
)
admin.add_view(UserAdminView(User, label="Users"))
admin.add_view(ModelView(Family))
admin.add_view(ModelView(Member))
admin.add_view(ModelView(Governor))
admin.add_view(ModelView(City))
admin.add_view(ModelView(RelationshipToHead))
admin.add_view(ModelView(ShelterQuality))
admin.add_view(ModelView(ShelterCenter))
admin.add_view(ModelView(ShelterBlock))

admin.mount_to(app)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"name": settings.PROJECT_NAME}


@app.get("/health")
def health_check():
    return {"status": "ok"}


def seed_superadmin():
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.role == UserRole.SUPERADMIN).first()
        if not exists:
            admin = User(
                username="admin",
                email="admin@camp.local",
                full_name="System Admin",
                hashed_password=get_password_hash("admin1234"),
                role=UserRole.SUPERADMIN,
            )
            db.add(admin)
            db.commit()
            print("✓ Superadmin created — username: admin / password: admin1234")
    finally:
        db.close()


seed_superadmin()


# 3. Main execution block to run the app using Uvicorn
if __name__ == "__main__":
    # The uvicorn.run() function starts the server.
    # The first argument specifies the application: "main:app"
    # means look for the 'app' object inside the 'main' module (main.py).
    # 'host' is the IP address to listen on (0.0.0.0 listens on all interfaces).
    # 'port' is the port number.
    # 'reload=True' enables auto-reloading during development.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
