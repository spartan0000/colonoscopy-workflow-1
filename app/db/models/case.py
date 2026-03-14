from sqlalchemy import Integer, String, Column, Text, JSON, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, relationship
from app.db.session import Base
from typing import List

class SampleTestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = Column(Integer, primary_key=True)
    report_text: Mapped[str] = Column(Text)
    parsed_output: Mapped[dict] = Column(JSON)
    recommendation: Mapped[dict] = Column(JSON)
    created_at: Mapped[DateTime] = Column(DateTime, server_default=func.now())

class SamplePatient(Base):
    __tablename__ = "sample_patients"

    patient_id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(200), nullable=False)
    nhi: Mapped[str] = Column(String(7), nullable=False)

    procedures: Mapped[List["SampleProcedure"]] = relationship("SampleProcedure", back_populates="patient")

class SampleProcedure(Base):
    __tablename__ = "sample_procedures"

    procedure_id: Mapped[int] = Column(Integer, primary_key=True)
    patient_id: Mapped[int] = Column(Integer, ForeignKey("sample_patients.patient_id"))
    date: Mapped[DateTime] = Column(DateTime, server_default=func.now())

    patient: Mapped["SamplePatient"] = relationship("SamplePatient", back_populates="procedures")
    triage: Mapped["SampleTriage"] = relationship("SampleTriage", back_populates="procedure")

class SampleTriage(Base):
    __tablename__ = "sample_triage"

    triage_id: Mapped[int] = Column(Integer, primary_key=True)
    procedure_id: Mapped[int] = Column(Integer, ForeignKey("sample_procedures.procedure_id"))
    raw_report: Mapped[str] = Column(String)
    normalized_data: Mapped[dict] = Column(JSON)
    final_recommendation: Mapped[dict] = Column(JSON)

    procedure: Mapped["SampleProcedure"] = relationship("SampleProcedure", back_populates="triage")