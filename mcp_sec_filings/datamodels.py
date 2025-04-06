import pydantic
import pydantic_settings
from typing import Annotated, Any
import datetime


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


