from fastapi import FastAPI
from app.routers.chat import router as chat_router
from app.routers.documents import router as document_router


app = FastAPI()


app.include_router(chat_router)
app.include_router(document_router)