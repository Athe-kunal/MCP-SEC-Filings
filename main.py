from mcp_sec_filings import constants, datamodels, sec_filings, pdf2md
import asyncio

async def main():
    sec_filings_request = datamodels.SECFilingsRequest(
        ticker="AMZN", year=2024, filing_types=["10-K", "10-Q"], include_amends=True
    )

    filings = await sec_filings.get_sec_filings_html_urls(sec_filings_request=sec_filings_request)

    mcpresults_pdf = sec_filings.sec_save_pdf(filings, sec_filings_request)

    await pdf2md.pdf2md_main(mcpresults_pdf)

if __name__ == "__main__":
    asyncio.run(main())