from fastapi import APIRouter
from app.api.v1.endpoints import families

api_router = APIRouter()

# Register the families endpoint
# This means the URL will be: /api/v1/families
api_router.include_router(families.router, prefix="/families", tags=["families"])

# You can keep your other routers here (auth, users, etc.)
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

