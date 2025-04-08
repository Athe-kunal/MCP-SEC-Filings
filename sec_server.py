from typing import Annotated
import asyncio
from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp_sec_filings import constants, datamodels, sec_filings

mcp = FastMCP("sec_filings")


async def process_sec_filings_request(
    sec_filings_request: datamodels.SECFilingsRequest, semaphore: asyncio.Semaphore
) -> list[datamodels.HTMLURLList] | None:
    async with semaphore:
        return await sec_filings.get_sec_filings_html_urls(
            sec_filings_request=sec_filings_request
        )


@mcp.tool
async def get_sec_filings(
    ticker: Annotated[str, "Stock ticker symbol"],
    year: Annotated[str | None, "Specific year for which filings are requested"],
    year_range: Annotated[
        str | None, "Range of years for filings in the format START_YEAR-END_YEAR"
    ],
    filing_types: Annotated[
        list[constants.SecFilingType], "Type(s) of SEC filings to retrieve"
    ],
    include_amends: bool,
) -> None:
    """
    Fetch SEC filings URLs for a given stock ticker, optionally filtered by year or year range.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL', 'GOOG').
        year (str | None): Specific year for which filings are requested.
            Provide only if fetching filings for a single year.
        year_range (str | None): Range of years for which filings are requested,
            specified as "START_YEAR-END_YEAR" (e.g., "2020-2023").
        filing_types (constants.SecFilingType): Type(s) of SEC filings to retrieve, such as 10-K, 10-Q, etc.
        include_amends (bool): Whether to include amended documents
    """
    assert not (
        year and year_range
    ), f"Both year and year range can't be set, only one of them can be set but got {year=} and {year_range=}"
    if year:
        sec_filings_request_list = [
            datamodels.SECFilingsRequest(
                ticker=ticker,
                year=int(year),
                filing_types=filing_types,
                include_amends=include_amends,
            )
        ]
    if year_range:
        year_break = year_range.split("-")
        start, end = int(year_break[0]), int(year_break[1])
        sec_filings_request_list = [
            datamodels.SECFilingsRequest(
                ticker=ticker,
                year=year,
                filing_types=filing_types,
                include_amends=include_amends,
            )
            for year in range(start, end + 1)
        ]

    semaphore = asyncio.Semaphore(5)
    tasks = [
        process_sec_filings_request(
            sec_filings_request=sec_filings_request, semaphore=semaphore
        )
        for sec_filings_request in sec_filings_request_list
    ]
    html_urls_list = await asyncio.gather(*tasks, return_exceptions=True)
    mcp_results: list[datamodels.MCPResults] = []
    for html_urls, sec_filings_request in zip(
        html_urls_list, sec_filings_request_list, strict=True
    ):
        if isinstance(html_urls, BaseException):
            logger.error(f"Unhandled error processing chunk: {html_urls}")
            continue
        if html_urls:
            mcp_results.extend(sec_filings.sec_save_pdf(
                html_urls=html_urls, sec_filings_request=sec_filings_request
            ))
    
