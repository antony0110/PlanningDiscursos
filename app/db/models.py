from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.db.database import Base


class Congregacion(Base):
    __tablename__ = "congregaciones"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False, index=True)

    # Relación con los oradores
    oradores = relationship("Orador", back_populates="congregacion_rel")


class Orador(Base):
    __tablename__ = "oradores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    cargo = Column(String)  # Ej: 'A', 'SM'
    es_coordinador = Column(Boolean, default=False)
    telefono = Column(String)
    email_jw = Column(String)
    email_personal = Column(String)
    
    congregacion_id = Column(Integer, ForeignKey("congregaciones.id"), nullable=False)

    # Relaciones
    congregacion_rel = relationship("Congregacion", back_populates="oradores")
    discursos = relationship("DiscursoOrador", back_populates="orador", cascade="all, delete-orphan")
    
    # AÑADE ESTA LÍNEA: Relación con planificacion (asumiendo backref o back_populates si lo tienes en Planificacion)
    planificaciones = relationship("Planificacion", backref="orador_rel", cascade="all, delete-orphan")

    
class DiscursoOrador(Base):
    """Guarda qué discursos (números de bosquejo) tiene preparados cada orador"""
    __tablename__ = "discursos_oradores"

    id = Column(Integer, primary_key=True, index=True)
    numero_discurso = Column(Integer, nullable=False, index=True)
    orador_id = Column(Integer, ForeignKey("oradores.id"), nullable=False)

    orador = relationship("Orador", back_populates="discursos")

    from sqlalchemy import Column, Integer, String
    from app.db.database import Base

class Bosquejo(Base):
    __tablename__ = "bosquejos"

    numero = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)


class Planificacion(Base):
    __tablename__ = 'planificacion'

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    id_orador = Column(Integer, ForeignKey('oradores.id'), nullable=True)
    numero_bosquejo = Column(Integer, ForeignKey('bosquejos.numero'), nullable=True)
    estado_invitacion = Column(String, default='No enviada')
    estado_confirmacion = Column(String, default='Pendiente')
    fecha_envio = Column(Date, nullable=True)
    token_confirmacion = Column(String, unique=True, nullable=True)
    es_evento_especial = Column(Boolean, default=False)
    texto_evento = Column(String, nullable=True)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    rol = Column(String, default="invitado")  # "admin" o "invitado"