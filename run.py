import uvicorn
from app.config import settings

if __name__ == "__main__":
    display_host = "localhost" if settings.HOST in ("0.0.0.0", "127.0.0.1") else settings.HOST
    print(f"\n=======================================================")
    print(f"🚀 {settings.PROJECT_NAME}")
    print(f"👉 Web Studio UI:  http://{display_host}:{settings.PORT}")
    print(f"👉 API Docs (Swagger): http://{display_host}:{settings.PORT}/docs")
    print(f"=======================================================\n")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

