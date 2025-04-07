from typing import Annotated
import httpx
from mcp.server.fastmcp import FastMCP
from mcp_sec_filings import constants

mcp = FastMCP("sec_filings")


@mcp.tool
async def get_sec_filings(
    ticker: Annotated[str, "Stock ticker symbol"],
    year: Annotated[str | None, "Specific year for which filings are requested"],
    year_range: Annotated[str | None, "Range of years for filings in the format START_YEAR-END_YEAR"],
    filing_types: Annotated[constants.SecFilingType, "Type(s) of SEC filings to retrieve"]
)->None:
    """
    Fetch SEC filings URLs for a given stock ticker, optionally filtered by year or year range.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL', 'GOOG').
        year (str | None): Specific year for which filings are requested. 
            Provide only if fetching filings for a single year.
        year_range (str | None): Range of years for which filings are requested, 
            specified as "START_YEAR-END_YEAR" (e.g., "2020-2023").
        filing_types (constants.SecFilingType): Type(s) of SEC filings to retrieve, such as 10-K, 10-Q, etc.
    """
    return

