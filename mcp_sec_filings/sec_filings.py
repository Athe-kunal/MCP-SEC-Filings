import re
import pandas as pd
from datetime import datetime
from typing import Union
import pdfkit
import os
import httpx
from loguru import logger
import concurrent.futures
from mcp_sec_filings import constants, datamodels

os.makedirs(constants.BASE_DIR, exist_ok=True)


def _search_url(cik: Union[str, int]) -> str:
    search_string = f"CIK={cik}&Find=Search&owner=exclude&action=getcompany"
    url = f"{constants.SEC_SEARCH_URL}?{search_string}"
    return url


async def get_cik_by_ticker(ticker: str) -> str:
    """Gets a CIK number from a stock ticker by running a search on the SEC website."""
    request_settings = datamodels.RequestSettings()
    url = _search_url(ticker)
    headers = {
        "User-Agent": f"{request_settings.company_name} {request_settings.email}",
        "Content-Type": "text/html",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        cik_re = re.compile(r".*CIK=(\d{10}).*")
        results = cik_re.findall(response.text)

    return str(results[0])


async def get_metadata_from_ticker(
    sec_filings_request: datamodels.SECFilingsRequest,
) -> tuple[str, dict[str, list[str]] | None]:
    cik = await get_cik_by_ticker(sec_filings_request.ticker)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = constants.SEC_CIK_URL.format(cik=cik)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Error fetching data for {sec_filings_request.model_dump_json()}: {exc}"
            )
            return cik, None

        json_data = response.json()

    return cik, json_data.get("filings", {}).get("recent")


def get_accession_list(
    recent_filings: dict[str, list[str]],
    sec_filings_request: datamodels.SECFilingsRequest,
) -> list[datamodels.AccessionNumElem]:
    acc_nums_list: list[datamodels.AccessionNumElem] = []
    sec_form_names: list[str] = []
    for acc_num, filing_name, filing_date, report_date in zip(
        recent_filings["accessionNumber"],
        recent_filings["form"],
        recent_filings["filingDate"],
        recent_filings["reportDate"],
    ):
        if filing_name in sec_filings_request.filing_types and report_date.startswith(
            str(sec_filings_request.year)
        ):
            if filing_name == "10-Q":
                datetime_obj = datetime.strptime(report_date, "%Y-%m-%d")
                quarter = pd.Timestamp(datetime_obj).quarter
                filing_name += str(quarter)
                if filing_name in sec_form_names:
                    filing_name += "-1"
            acc_nums_list.append(
                datamodels.AccessionNumElem.from_accession_metadata(
                    accession_num=acc_num,
                    filing_name=filing_name,
                    filing_date=filing_date,
                    report_date=report_date,
                )
            )
            sec_form_names.append(filing_name)
    return acc_nums_list


def make_ticker_year_path(sec_filings_request: datamodels.SECFilingsRequest) -> str:
    ticker_year_path = os.path.join(
        constants.BASE_DIR, f"{sec_filings_request.ticker}-{sec_filings_request.year}"
    )
    os.makedirs(ticker_year_path, exist_ok=True)
    return ticker_year_path


async def get_sec_filings_html_urls(
    sec_filings_request: datamodels.SECFilingsRequest,
) -> list[datamodels.HTMLURLList] | None:
    cik, recent_filings = await get_metadata_from_ticker(sec_filings_request)
    if not recent_filings:
        logger.error(f"Could not retrieve for {sec_filings_request.model_dump()}")
        return None
    acc_nums_list = get_accession_list(
        recent_filings=recent_filings, sec_filings_request=sec_filings_request
    )
    html_urls = [
        datamodels.HTMLURLList.from_cik_accnum_ticker(
            cik=cik, acc_num=acc_num, ticker=sec_filings_request.ticker
        )
        for acc_num in acc_nums_list
    ]
    return html_urls


def sec_save_pdf(
    html_urls: list[datamodels.HTMLURLList],
    sec_filings_request: datamodels.SECFilingsRequest,
) -> list[datamodels.MCPResults]:
    ticker_year_path = make_ticker_year_path(sec_filings_request=sec_filings_request)
    mcp_results = convert_html_to_pdfs(html_urls, ticker_year_path)
    return mcp_results


def _convert_single_html_to_pdf(
    html_url: datamodels.HTMLURLList, base_path: str
) -> datamodels.MCPResults:
    pdf_path = html_url.html_url.split("/")[-1]
    pdf_path = pdf_path.replace(".htm", f"-{html_url.filing_name}.pdf")
    pdf_path = pdf_path.replace("/A", "A")
    pdf_path = os.path.join(base_path, pdf_path)

    pdfkit.from_url(html_url.html_url, pdf_path)
    logger.info(f"Saved filing {html_url.filing_name} at {pdf_path=}")

    return datamodels.MCPResults(
        rgld_cik=html_url.rgld_cik,
        html_url=html_url.html_url,
        filing_name=html_url.filing_name,
        pdf_path=os.path.abspath(pdf_path),
    )


def convert_html_to_pdfs(
    html_urls: list[datamodels.HTMLURLList], base_path: str
) -> list[datamodels.MCPResults]:

    mcp_results: list[datamodels.MCPResults] = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(_convert_single_html_to_pdf, html_url, base_path)
            for html_url in html_urls
        ]
        for future in futures:
            mcp_results.append(future.result())

    return mcp_results
