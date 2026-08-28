from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.api.routes.health import router as health_router
from app.database.mongodb import check_database_connection
from app.api.routes.database import router as database_router
from app.api.routes.navigation import router as navigation_router
from app.api.routes.user import router as user_router
from app.api.routes.puja import router as puja_router
from app.api.routes.kundali import router as kundali_router
from app.api.routes.muhurat import router as muhurat_router
from app.api.routes.pandit import router as pandit_router
from app.api.routes.contact import router as contact_router
from app.api.routes.voice import router as voice_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

print("Application Name:", settings.APP_NAME)
print("Version:", settings.APP_VERSION)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_database_connection()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for AI-powered Voice Navigation System",
    lifespan=lifespan
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(database_router)
app.include_router(navigation_router)
app.include_router(puja_router)
app.include_router(kundali_router)
app.include_router(muhurat_router)
app.include_router(pandit_router)
app.include_router(contact_router)
app.include_router(user_router)
app.include_router(voice_router)

from app.api.routes.admin import router as admin_router
app.include_router(admin_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to MantraSetu Saarthi Backend 🚀"
    }
