from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()
engine = create_engine(
    "sqlite:///:memory:",
    echo=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    # Seed data for assessment
    if not session.query(UserModel).filter_by(id=1).first():
        session.add(UserModel(id=1, name="Candidate One", email="test@example.com"))
        session.commit()
    session.close()
