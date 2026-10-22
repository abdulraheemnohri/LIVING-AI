import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "living_ai.app:app",
        host=os.getenv("LIVING_AI_HOST", "127.0.0.1"),
        port=int(os.getenv("LIVING_AI_PORT", "8000")),
        reload=False,
    )
