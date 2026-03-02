from typing import List, Literal
from pydantic import BaseModel, Field
from typing_extensions import Annotated

class Polyp(BaseModel):
    location: Literal[
        "cecum",
        "ascending_colon",
        "hepatic_flexure",
        "transverse_colon",
        "splenic_flexure",
        "descending_colon",
        "sigmoid_colon",
        "rectum"
    ]
    size: Annotated[int, Field(ge=0)]  # size in millimeters
    type: Literal[
        "adenoma",
        "tubulovillous_or_villous_adenoma",
        "sessile_serrated_polyp",
        "hyperplastic_polyp",
        "normal_colonic_mucosa"
    ]
    dysplasia: Literal["none", "low_grade", "high_grade"]
    resection: Literal["complete", "piecemeal", "not_resected", "unknown"]
    retrieval: Literal["complete", "incomplete", "unknown"]

class Biopsy(BaseModel):
    location: Literal[
        "cecum",
        "ascending_colon",
        "hepatic_flexure",
        "transverse_colon",
        "splenic_flexure",
        "descending_colon",
        "sigmoid_colon",
        "rectum"
    ]
    indication: Literal[
        "inflammation",
        "ulceration",
        "stricture",
        "other"
    ]
    result: Literal[
        "normal_colonic_mucosa",
        "active_inflammation",
        "chronic_inflammation",
        "granulomas",
        "dysplasia",
        "malignancy"
    ]

class BostonBowelPrepScore(BaseModel):
    total: Annotated[int, Field(ge=0, le=9)]
    right: Annotated[int, Field(ge=0, le=3)]
    transverse: Annotated[int, Field(ge=0, le=3)]
    left: Annotated[int, Field(ge=0, le=3)]

class Colonoscopy(BaseModel):
    date: str  # YYYY-MM-DD format
    number_of_polyps: Annotated[int, Field(ge=0)]
    cecum_reached: Literal["yes", "no"]
    bostonBowelPrepScore: BostonBowelPrepScore
    polyps: List[Polyp]
    biopsies: List[Biopsy]

class ColonoscopySummary(BaseModel):
    patient_name: str
    patient_NHI: str
    patient_age: Annotated[int, Field(ge=0)]
    indication: Literal[
        "sps",
        "ibd",
        "family_history_category_1",
        "family_history_category_2",
        "family_history_category_3",
        "family_history_unknown",
        "positive_faecal_immunochemical_test",
        "anaemia",
        "rectal_bleeding",
        "change_in_bowel_habit",
        "abdominal_pain",
        "weight_loss",
        "surveillance_for_previous_polyps",
        "screening",
        "other",
        "unknown"
    ]
    colonoscopy: List[Colonoscopy]