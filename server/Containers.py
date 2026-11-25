
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ContainerCreate(BaseModel):
    container_number: str = Field(
        alias="מספר מכולה"
    )

    start_time: datetime | None = Field(
        default=None,
        alias="שעת התחלה"
    )

    end_time: datetime | None = Field(
        default=None,
        alias="שעת סיום"
    )

    status: str | None = Field(
        default=None,
        alias="סטטוס"
    )

    attachments: list[dict[str, Any]] | None = Field(
        default=None,
        alias="Attachments"
    )

    supplier: str | None = Field(
        default=None,
        alias="ספק"
    )

    transport_company: str | None = Field(
        default=None,
        alias="חברת הובלה"
    )

    driver_name: str | None = Field(
        default=None,
        alias="שם נהג"
    )

    truck_number: str | None = Field(
        default=None,
        alias="מספר משאית"
    )

    unloader: list[str] | None = Field(
        default=None,
        alias="פורק"
    )

    forklift_operator: list[str] | None = Field(
        default=None,
        alias="מלגזן"
    )

    assistant_forklift_operator: list[str] | None = Field(
        default=None,
        alias="עוזר מלגזן"
    )

    pallet_location_worker: list[str] | None = Field(
        default=None,
        alias="מזין משטחים במיקום"
    )

