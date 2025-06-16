from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from single_video_routes import router as single_video_router
from playlist_routes import router as playlist_router

app = FastAPI()

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(single_video_router)
app.include_router(playlist_router)