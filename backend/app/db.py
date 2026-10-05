"""
Database layer.
- Set DATABASE_URL to your Supabase Postgres connection string in production.
- If DATABASE_URL is not set, a local SQLite file is used so the app runs offline.
"""
import os
from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, Integer, String, create_engine,
                        func, select)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")

# Supabase gives "postgres://" in some places; SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class CrowdReport(Base):
    __tablename__ = "crowd_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route = Column(String(10), nullable=False, index=True)
    direction = Column(String(20), nullable=False)
    crowd_level = Column(Integer, nullable=False)  # 0..3
    stop_name = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc), index=True)


def init_db():
    # Safe on Supabase too: only creates the table if it doesn't exist.
    Base.metadata.create_all(bind=engine)


def recent_reports(session, route: str, direction: str, since: datetime):
    stmt = (select(CrowdReport)
            .where(CrowdReport.route == route,
                   CrowdReport.direction == direction,
                   CrowdReport.created_at >= since)
            .order_by(CrowdReport.created_at.desc()))
    return list(session.scalars(stmt))


def count_reports(session) -> int:
    return session.scalar(select(func.count(CrowdReport.id))) or 0
