from typing import List
import re
import pandas as pd
from datetime import datetime
from typing import Union
import requests
import pdfkit
import os
from mcp_sec_filings import constants, datamodels

os.makedirs(constants.BASE_DIR,exist_ok=True)

def _search_url(cik: Union[str, int]) -> str:
    search_string = f"CIK={cik}&Find=Search&owner=exclude&action=getcompany"
    url = f"{constants.SEC_SEARCH_URL}?{search_string}"
    return url

def get_cik_by_ticker(ticker: str) -> str:
    """Gets a CIK number from a stock ticker by running a search on the SEC website."""
    request_settings = datamodels.RequestSettings()
    url = _search_url(ticker)
    headers = {
        "User-Agent": f"{request_settings.company_name} {request_settings.email}",
        "Content-Type": "text/html",
    }
    response = requests.get(url, stream=True, headers=headers)
    response.raise_for_status()
    cik_re = re.compile(r".*CIK=(\d{10}).*")
    results = cik_re.findall(response.text)
    assert len(results) == 1, f"Expected 1 result match, but got {response.text=} and {results=}"
    return str(results[0])


def sec_save_pdfs(sec_filings_request: datamodels.SECFilingsRequest) -> None:
    cik = get_cik_by_ticker(sec_filings_request.ticker)
    rgld_cik = int(cik.lstrip("0"))
    ticker_year_path = os.path.join(constants.BASE_DIR,f"{sec_filings_request.ticker}-{sec_filings_request.year}")
    os.makedirs(ticker_year_path, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = constants.SEC_CIK_URL.format(cik=cik)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_data = response.json()
    else:
        print(f"Error: Unable to fetch data. Status code: {response.status_code}")

    form_lists = []
    filings = json_data["filings"]
    recent_filings = filings["recent"]
    sec_form_names = []
    for acc_num, form_name, filing_date, report_date in zip(
        recent_filings["accessionNumber"],
        recent_filings["form"],
        recent_filings["filingDate"],
        recent_filings["reportDate"],
    ):
        if form_name in forms and report_date.startswith(str(sec_filings_request.year)):
            if form_name == "10-Q":
                datetime_obj = datetime.strptime(report_date, "%Y-%m-%d")
                quarter = pd.Timestamp(datetime_obj).quarter
                form_name += str(quarter)
                if form_name in sec_form_names:
                    form_name += "-1"
            no_dashes_acc_num = re.sub("-", "", acc_num)
            form_lists.append([no_dashes_acc_num, form_name, filing_date, report_date])
            sec_form_names.append(form_name)
    process_links = lambda x: "".join(x.split("-"))

    acc_nums_list = [[fl[0],fl[1],process_links(fl[-1])] for fl in form_lists]
    
    html_urls = [[f"{constants.SEC_EDGAR_URL}/{rgld_cik}/{acc}/{sec_filings_request.ticker.lower()}-{report_date}.htm",filing_type] for acc,filing_type,report_date in acc_nums_list]
    
    metadata_json = _convert_html_to_pdfs(html_urls,ticker_year_path)
    
    # with open(os.path.join(ticker_year_path,'metadata.json'), 'w') as f:
    #     json.dump(metadata_json, f)
    return html_urls, metadata_json, ticker_year_path

def _convert_html_to_pdfs(html_urls,base_path:str):
    metadata_json = {}
    for html_url in html_urls:
        pdf_path = html_url[0].split("/")[-1]
        # Add the filing type
        pdf_path = pdf_path.replace(".htm",f"-{html_url[1]}.pdf")
        # /A for amended is not a valid path
        pdf_path = pdf_path.replace("/A","A")
        metadata_json[pdf_path] = {"languages":["English"]}
        pdf_path = os.path.join(base_path,pdf_path)
        pdfkit.from_url(html_url[0], pdf_path)
    return metadata_json