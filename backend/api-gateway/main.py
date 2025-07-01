from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn

app = FastAPI(title="PuzzleCraft AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from routers import auth, puzzles, games, users
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(puzzles.router, prefix="/api/v1/puzzles", tags=["puzzles"])
app.include_router(games.router, prefix="/api/v1/games", tags=["games"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "PuzzleCraft AI API Gateway"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
