# db.py
from sqlalchemy import create_engine, Column, Integer, String, Date, Text
from sqlalchemy.orm import sessionmaker, declarative_base
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    senha = Column(String)

class Operacao(Base):
    __tablename__ = 'operacoes'
    id = Column(Integer, primary_key=True)
    edicao = Column(String)
    nome_operacao = Column(String)
    data = Column(Date)
    descricao = Column(Text)
    pessoas_abordadas = Column(Integer)
    estabelecimentos_fiscalizados = Column(Integer)
    pessoas_conduzidas = Column(Integer)
    tco = Column(Integer)
    interditados = Column(Integer)
    apreensoes = Column(Text) # Continua sendo Text, mas armazenará JSON com [{tipo, quantidade}]
    locais = Column(Text)
    forcas = Column(Text)  # JSON com [{nome, viaturas}]
    imagens = Column(Text)

def get_engine():
    return create_engine("sqlite:///test.db")

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()