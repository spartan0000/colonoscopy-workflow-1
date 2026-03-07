from sqlalchemy import Integer, String, Column, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped
from app.db.session import Base

class SampleTestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = Column(Integer, primary_key=True)
    report_text: Mapped[str] = Column(Text, nullable=False)
    parsed_output: Mapped[dict] = Column(JSON, nullable=False)
    recommendation: Mapped[dict] = Column(JSON, nullable=False)
    created_at: Mapped[DateTime] = Column(DateTime, server_default=func.now(), nullable=False)

    