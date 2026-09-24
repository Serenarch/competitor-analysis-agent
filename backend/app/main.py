from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import analysis, history

app = FastAPI(
    title="智能竞品分析 Agent",
    description="基于 LangGraph + LangSmith 的自动化竞品分析系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(analysis.router)
app.include_router(history.router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "竞品分析 Agent",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)