"""Structured extraction schema sent to Muse Spark."""

from typing import Optional

from pydantic import BaseModel, Field


class AgreementExtraction(BaseModel):
    """Six agreement fields, each with the clause that supports it."""

    agreement_value: Optional[int] = Field(
        description=(
            "Periodic rent as an integer with no currency symbol or separators. "
            "Null when the document does not state the rent."
        )
    )
    agreement_value_quote: str = Field(
        description="Exact source clause for the rent. Empty when the value is null."
    )
    agreement_start_date: Optional[str] = Field(
        description="Lease start date as DD.MM.YYYY. Null when it cannot be determined."
    )
    agreement_start_date_quote: str = Field(
        description="Exact source clause for the start date. Empty when the value is null."
    )
    agreement_end_date: Optional[str] = Field(
        description="Lease end date as DD.MM.YYYY. Null when it cannot be determined."
    )
    agreement_end_date_quote: str = Field(
        description="Exact source clause for the end date, or for the duration used to compute it. Empty when the value is null."
    )
    renewal_notice_days: Optional[int] = Field(
        description=(
            "Notice required before terminating or vacating, in days. "
            "Null when the document states no notice period."
        )
    )
    renewal_notice_days_quote: str = Field(
        description="Exact source clause for the notice period. Empty when the value is null."
    )
    party_one: Optional[str] = Field(
        description="Name of the owner side. Null when it cannot be identified."
    )
    party_one_quote: str = Field(
        description="Exact source clause naming party one. Empty when the value is null."
    )
    party_two: Optional[str] = Field(
        description="Name of the tenant side. Null when it cannot be identified."
    )
    party_two_quote: str = Field(
        description="Exact source clause naming party two. Empty when the value is null."
    )
