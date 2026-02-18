import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.dashboard_routes import dashboard_router
from app.api.busca_routes import busca_router

from dotenv import load_dotenv
load_dotenv()




app = FastAPI()

origins = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     # ou ["*"] durante dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(busca_router)
