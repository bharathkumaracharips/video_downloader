from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from single_video_routes import router as single_video_router
from playlist_routes import router as playlist_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(single_video_router)
app.include_router(playlist_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)