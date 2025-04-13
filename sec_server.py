import os
from typing import Annotated
import asyncio
from loguru import logger
import pathlib
import json
import pydantic
from mcp import types
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


def get_sec_filings_request(
    year: str | None,
    year_range: str | None,
    ticker: str,
    filing_types: list[constants.SecFilingType],
    include_amends: bool,
) -> list[datamodels.SECFilingsRequest]:
    sec_filings_request_list: list[datamodels.SECFilingsRequest] = []
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
        start, end = map(int, year_range.split("-"))
        sec_filings_request_list = [
            datamodels.SECFilingsRequest(
                ticker=ticker,
                year=year,
                filing_types=filing_types,
                include_amends=include_amends,
            )
            for year in range(start, end + 1)
        ]
    return sec_filings_request_list


@mcp.tool(
    name="get_sec_filings_save_pdf",
    description="Fetch SEC filings URLs for a given stock ticker, optionally filtered by year or year range.",
)
async def get_sec_filings_save_pdf(
    ticker: Annotated[str, "Stock ticker symbol"],
    year: Annotated[str | None, "Specific year for which filings are requested"],
    year_range: Annotated[
        str | None, "Range of years for filings in the format START_YEAR-END_YEAR"
    ],
    filing_types: Annotated[
        list[constants.SecFilingType], "Type(s) of SEC filings to retrieve"
    ],
    include_amends: Annotated[bool, "Whether to include amended documents"],
) -> None:
    """
    Fetch SEC filings URLs for a given stock ticker, optionally filtered by year or year range and then finally saves the pdf

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL', 'GOOG').
        year (str | None): Specific year for which filings are requested.
            Provide only if fetching filings for a single year.
        year_range (str | None): Range of years for which filings are requested,
            specified as "START_YEAR-END_YEAR" (e.g., "2020-2023").
        filing_types (constants.SecFilingType): Type(s) of SEC filings to retrieve, such as 10-K, 10-Q, etc.
        include_amends (bool): Whether to include amended documents

    Raises:
        AssertionError: If both year and year range are set
    """
    assert not (
        year and year_range
    ), f"Both year and year range can't be set, only one of them can be set but got {year=} and {year_range=}"

    sec_filings_request_list = get_sec_filings_request(
        year=year,
        year_range=year_range,
        ticker=ticker,
        filing_types=filing_types,
        include_amends=include_amends,
    )
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "5"))
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        process_sec_filings_request(
            sec_filings_request=sec_filings_request, semaphore=semaphore
        )
        for sec_filings_request in sec_filings_request_list
    ]
    html_urls_list = await asyncio.gather(*tasks, return_exceptions=True)
    mcp_results: list[datamodels.MCPResultsPDF] = []
    for html_urls, sec_filings_request in zip(
        html_urls_list, sec_filings_request_list, strict=True
    ):
        if isinstance(html_urls, BaseException):
            logger.error(f"Unhandled error processing chunk: {html_urls}")
            continue
        if html_urls:
            mcp_results.extend(
                sec_filings.sec_save_pdf(
                    html_urls=html_urls, sec_filings_request=sec_filings_request
                )
            )


@mcp.list_resources()
async def list_resources() -> list[types.Resource]:
    json_data: dict[str, list[dict[str, str]]] = {}
    for json_file in pathlib.Path(constants.BASE_DIR).rglob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                json_data[json_file.stem] = data
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode {json_file}: {e}")

    resources = [
        types.Resource(
            uri=pydantic.FileUrl(f"file:///{val['pdf_path']}"),
            name=f"{val['ticker']: {val['filing_name']}}",
            description=f"The {val['filing_name']} for the ticker symbol {val['ticker']}",
            mimeType="application/pdf",
        )
        for _, vals in json_data.items()
        for val in vals
    ]
    return resources
