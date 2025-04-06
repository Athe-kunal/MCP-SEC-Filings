import pydantic
import pydantic_settings
from typing import Annotated, Any
import datetime

import re

from mcp_sec_filings import constants

class RequestSettings(pydantic_settings.BaseSettings):
    company_name: str = "IU"
    email: str = "athe@stonks.com"

    class Config:
        env_file = ".env"

class SECFilingsRequest(pydantic.BaseModel):
    ticker: Annotated[str, "Ticker symbol"]
    year: Annotated[int, "The year for getting the documents", pydantic.Field(alias="year",ge=2000,le=datetime.datetime.now().year)] 
    filing_types: list[constants.SecFilingType]
    include_amends: bool

    def model_post_init(self, __context: Any) -> None:
        self.ticker = self.ticker.upper()

def validate_date(date_str: str) -> str:
    try:
        datetime.datetime.strptime(date_str,"%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"The date format YYYY-MM-DD failed for {date_str=}")
    return date_str

class AccessionNumElem(pydantic.BaseModel):
    accession_num: str
    no_dashes_accession_num: str | None = None
    filing_name: str
    filing_date: Annotated[str,"Filing Date",pydantic.AfterValidator(validate_date)]
    report_date: Annotated[str,"Report Date",pydantic.AfterValidator(validate_date)]
    no_dashes_report_date: str | None = None

    def model_post_init(self, __context: Any) -> None:
        self.no_dashes_accession_num = re.sub("-", "", self.accession_num)
        self.no_dashes_report_date = "".join(self.report_date.split("-"))

class HTMLURLList(pydantic.BaseModel):
    rgld_cik: int
    html_url: str
    filing_name: str

    @classmethod
    def from_cik_accnum_ticker(cls, cik: str, acc_num: "AccessionNumElem", ticker: str) -> "HTMLURLList":
        rgld_cik = int(cik.lstrip("0"))
        html_url = f"{constants.SEC_EDGAR_URL}/{rgld_cik}/{acc_num.no_dashes_accession_num}/{ticker.lower()}-{acc_num.no_dashes_report_date}.htm"
        filing_name = acc_num.filing_name
        return cls(rgld_cik=rgld_cik, html_url=html_url, filing_name=filing_name)
