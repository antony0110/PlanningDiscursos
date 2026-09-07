from typing import List, Optional
from pydantic import BaseModel
from datetime import date

class DiscursoOradorOut(BaseModel):
    id: int
    numero_discurso: int

    class Config:
        from_attributes = True
        orm_mode = True

class OradorOut(BaseModel):
    id: int
    nombre: str
    cargo: Optional[str] = None
    es_coordinador: bool = False
    telefono: Optional[str] = None
    email_jw: Optional[str] = None
    email_personal: Optional[str] = None
    congregacion_id: int
    discursos: List[DiscursoOradorOut] = []  # 👈 Devuelve objetos con 'numero_discurso' para que el JS los lea bien

    class Config:
        from_attributes = True
        orm_mode = True

class CongregacionOut(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True
        orm_mode = True

class PlanificacionResponse(BaseModel):
    id: int
    fecha: date
    id_orador: Optional[int] = None
    orador_nombre: Optional[str] = None
    orador_telefono: Optional[str] = None
    orador_congregacion: Optional[str] = None
    numero_bosquejo: Optional[int] = None
    bosquejo_tema: Optional[str] = None
    estado_invitacion: Optional[str] = "No enviada"
    estado_confirmacion: Optional[str] = "Pendiente"
    fecha_envio_invitacion: Optional[date] = None
    es_evento_especial: Optional[bool] = False
    texto_evento: Optional[str] = None

    class Config:
        from_attributes = True

class PlanificacionUpdate(BaseModel):
    id_orador: Optional[int] = None
    numero_bosquejo: Optional[int] = None
    estado_invitacion: Optional[str] = None
    estado_confirmacion: Optional[str] = None
    es_evento_especial: Optional[bool] = None
    texto_evento: Optional[str] = None

class UsuarioCreate(BaseModel):
    username: str
    password: str
    rol: Optional[str] = "invitado"

class UsuarioLogin(BaseModel):
    username: str
    password: str

class UsuarioOut(BaseModel):
    id: int
    username: str
    rol: str

    class Config:
        from_attributes = True

class LoginSchema(BaseModel):
    username: str
    password: str