import uvicorn
from app.main import app

if __name__ == "__main__":
    # Production configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Allow connections from any IP
        port=8000,
        reload=False,    # Disable reload in production
        workers=1,        # Single worker for SQLite
        log_level="info",
        access_log=True
    )
