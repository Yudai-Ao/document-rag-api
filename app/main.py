from fastapi import FastAPI
from app.routers.chat import router as chat_router
from app.routers.documents import router as document_router
from app.schemas.health import HealthResponse


app = FastAPI()


@app.get(
    "/health",
    response_model=HealthResponse
)
def health_check():
    return HealthResponse(
        status="ok"
    )

app.include_router(chat_router)
app.include_router(document_router)

