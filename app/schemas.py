"""Request and response models. FastAPI uses these to validate input and document the API."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class BondOut(BaseModel):
    code: str
    coupon_percent: float
    maturity: date
    coupon_dates: list[str] = Field(description="Interest payment dates as DD/MM")


class CashFlow(BaseModel):
    date: date
    amount: float = Field(description="Cash flow per R100 nominal")


class ScheduleOut(BaseModel):
    code: str
    settle: date
    cash_flows: list[CashFlow]


class PriceOut(BaseModel):
    code: str
    settle: date
    ytm_percent: float
    ex_coupon: bool
    accrued_interest: float
    clean_price: float
    all_in_price: float


class YieldOut(BaseModel):
    code: str
    settle: date
    clean_price: float
    ytm_percent: float


class QuoteIn(BaseModel):
    code: str = Field(examples=["R2032"])
    settle: date
    ytm_percent: float = Field(gt=-50, lt=100, examples=[8.9])
    source: str = Field(default="manual", max_length=50)


class QuoteOut(QuoteIn):
    id: int
    clean_price: float
    created_at: datetime
