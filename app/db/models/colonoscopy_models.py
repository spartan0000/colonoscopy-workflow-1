from sqlalchemy import Index, JSON, CheckConstraint, UniqueConstraint, Column, Integer, String, ForeignKey, Boolean, Float, create_engine, DateTime, Date, func
from sqlalchemy.orm import relationship, sessionmaker, Mapped, mapped_column, declarative_base
from app.db.session import Base
import os
from dotenv import load_dotenv

from typing import List

from datetime import date

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")




class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        Index("idx_dob", "dob"),

    )

    patient_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nhi: Mapped[str] = mapped_column(String(7), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[Date] = mapped_column(Date, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    procedures: Mapped[List["Procedure"]] = relationship("Procedure", back_populates="patient")

class Procedure(Base):
    __tablename__ = "procedures"
    __table_args__ = (
        Index("idx_proc_patient_date", "patient_id", "procedure_date"),
        UniqueConstraint("patient_id", "procedure_date", name="uix_patient_procedure_date")
    )
    procedure_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    procedure_date: Mapped[Date] = mapped_column(Date, nullable=False)
    observed_age: Mapped[int] = mapped_column(Integer, nullable=False)
    endoscopist: Mapped[str] = mapped_column(String(100), nullable=False)
    cecum_reached: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bbps_total: Mapped[int] = mapped_column(Integer, nullable=False)
    bbps_right: Mapped[int] = mapped_column(Integer, nullable=False)
    bbps_transverse: Mapped[int] = mapped_column(Integer, nullable=False)
    bbps_left: Mapped[int] = mapped_column(Integer, nullable=False)
    indication: Mapped[str] = mapped_column(String(250))
    withdrawal_time: Mapped[float] = mapped_column(Float, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    patient: Mapped["Patient"] = relationship("Patient", back_populates="procedures")
    findings: Mapped[List["Finding"]] = relationship("Finding", back_populates="procedure", cascade="all, delete-orphan")
    #specimens: Mapped[List["Specimen"]] = relationship("Specimen", back_populates="procedure", cascade="all, delete-orphan")
    histologies: Mapped[List["Histology"]] = relationship("Histology", back_populates="procedure", cascade="all, delete-orphan")
    triage: Mapped["Triage"] = relationship("Triage", back_populates="procedure", uselist=False, cascade="all, delete-orphan")

class Finding(Base): #findings represent what's seen during the procedure.  Used for documentation only
    __tablename__ = "findings"
    finding_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey("procedures.procedure_id"), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False) #for example, polyp, ulcer, inflammation, diverticulum etc.
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    size_mm: Mapped[float] = mapped_column(Float)
    polyp: Mapped[bool] = mapped_column(Boolean) #is the finding a polyp or not
    biopsied: Mapped[bool] = mapped_column(Boolean)
    resection_method: Mapped[str] = mapped_column(String(50)) #cold snare, hot snare, lift, etc.
    resection_complete: Mapped[bool] = mapped_column(Boolean)
    retrieval_complete: Mapped[bool] = mapped_column(Boolean)


    #specimens: Mapped[List["Specimen"]] = relationship(secondary="finding_specimen", back_populates="findings") #many to many relationship with specimens, as one finding can have multiple specimens sent, and one specimen can be associated with multiple findings if more than one polyp sent in the same specimen pot.)
    procedure: Mapped["Procedure"] = relationship("Procedure", back_populates="findings")
    

# class Specimen(Base):
#     __tablename__ = "specimens"
#     specimen_id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey("procedures.procedure_id"), ondelete="CASCADE", nullable=False)
#     label: Mapped[str] = mapped_column(String(100), nullable=False)
#     collected_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

#     procedure: Mapped["Procedure"] = relationship("Procedure", back_populates="specimens")
#     histologies: Mapped[List["Histology"]] = relationship("Histology", back_populates="specimen") #left out the cascade delete here because we want to keep the histology records even if the specimen record is deleted, as long as the procedure record is still there. If the procedure record is deleted, then all associated specimen and histology records will be deleted due to the cascade delete on the procedure_id foreign key in both tables.
#     findings: Mapped[List["Finding"]] = relationship(secondary="finding_specimen", back_populates="specimens")
    

class Histology(Base): #histology represents the pathology results and is used for triaging.  
    __tablename__ = "histology"
    histology_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #specimen_id: Mapped[int] = mapped_column(Integer, ForeignKey("specimens.specimen_id", ondelete="CASCADE"), nullable=False) #one to many - one specimen can have multiple histology if more than one polyp in each specimen sent
    procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey("procedures.procedure_id"), nullable=False)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    is_polyp: Mapped[bool] = mapped_column(Boolean, nullable=False)
    size_mm: Mapped[float] = mapped_column(Float)
    
    histology: Mapped[str] = mapped_column(String(100), nullable=False)
    dysplasia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dysplasia_grade: Mapped[str] = mapped_column(String(50))

    procedure: Mapped["Procedure"] = relationship("Procedure", back_populates="histologies")
    
    #specimen: Mapped["Specimen"] = relationship("Specimen", back_populates="histologies")

# class FindingSpecimen(Base):
#     __tablename__ = "finding_specimen"
#     finding_id: Mapped[int] = mapped_column(Integer, ForeignKey("findings.finding_id", ondelete="CASCADE"), primary_key=True)
#     specimen_id: Mapped[int] = mapped_column(Integer, ForeignKey("specimens.specimen_id", ondelete="CASCADE"), primary_key=True)


class Triage(Base):
    __tablename__ = "triage"
    
    triage_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    procedure_id: Mapped[int] = mapped_column(Integer, ForeignKey("procedures.procedure_id"), ondelete="CASCADE", nullable=False) # a procedure can have more than one triage decision if these change over time, so I left out the unique=True
    raw_histology_text: Mapped[str] = mapped_column(String, nullable=False)
    histology_json: Mapped[dict] = mapped_column(JSON)
    triage_decision: Mapped[dict] = mapped_column(JSON, nullable=False)
    triage_date_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)


    procedure: Mapped["Procedure"] = relationship("Procedure", back_populates="triage")