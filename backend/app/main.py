
import uvicorn

from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.dashboard_routes import dashboard_router
from app.api.busca_routes import busca_router
from app.api.modelo_routes import modelo_router 

app = FastAPI()

origins = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Cobre também outras portas do Vite (ele sobe em 5174, 5175... se 5173
    # já estiver ocupada) e acesso via 127.0.0.1 em qualquer porta — sem
    # isso, o fetch do frontend falha com "Failed to fetch" mesmo que o
    # backend processe e logue 200 OK (o navegador descarta a resposta por
    # causa do CORS antes de entregá-la ao JS). Não há uso de cookies/sessão
    # nesta API (só GETs públicos), então allow_credentials não é necessário
    # e dispensa manter allow_origins como uma lista fechada.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(busca_router)
app.include_router(modelo_router)
