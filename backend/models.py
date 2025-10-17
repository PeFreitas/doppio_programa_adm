from sqlalchemy import Column, Integer, String, Float, DateTime
from .database import Base

class Venda(Base):
    __tablename__ = "vendas"

    id = Column(Integer, primary_key=True, index=True)
    id_externo = Column(String, unique=True, index=True) # ID da venda na API de origem
    produto = Column(String, index=True)
    quantidade = Column(Integer)
    valor_unitario = Column(Float)
    valor_total = Column(Float)
    data_venda = Column(DateTime)
    origem = Column(String) # Para saber se veio do Conta Azul ou TOTVS