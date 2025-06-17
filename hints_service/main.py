from fastapi import FastAPI
from .api.endpoints import hints

app = FastAPI()
app.include_router(hints.router)
