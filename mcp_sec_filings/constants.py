from typing import Final
from typing_extensions import Literal

SEC_SEARCH_URL: Final[str] = "http://www.sec.gov/cgi-bin/browse-edgar"
SEC_EDGAR_URL: Final[str] = "https://www.sec.gov/Archives/edgar/data"

SEC_CIK_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

BASE_DIR = "SEC_EDGAR_FILINGS"


SecFilingType = Literal[
    "10-K",
    "10-K/A",  # Annual report + Amended
    "10-Q",
    "10-Q/A",  # Quarterly report + Amended
    "8-K",
    "8-K/A",  # Current report + Amended
    "S-1",
    "S-1/A",  # Registration statement (IPO) + Amended
    "S-3",
    "S-3/A",  # Registration for seasoned issuers + Amended
    "S-4",
    "S-4/A",  # Securities issued in mergers + Amended
    "S-8",
    "S-8/A",  # Registration of employee stock plans + Amended
    "S-11",
    "S-11/A",  # Registration for REITs + Amended
    "F-1",
    "F-1/A",  # Foreign IPO + Amended
    "F-3",
    "F-3/A",  # Foreign seasoned issuers + Amended
    "F-4",
    "F-4/A",  # Foreign M&A filings + Amended
    "20-F",
    "20-F/A",  # Annual report (foreign companies) + Amended
    "6-K",  # Semi-annual report (foreign companies) - no /A
    "DEF 14A",
    "DEF 14A/A",  # Definitive proxy statement + Amended
    "13D",
    "13D/A",  # Beneficial ownership report (>5%) + Amended
    "13G",
    "13G/A",  # Short-form beneficial ownership report (>5%) + Amended
    "SC 13D",
    "SC 13D/A",  # Schedule 13D + Amended
    "SC 13G",
    "SC 13G/A",  # Schedule 13G + Amended
    "Form 3",
    "Form 3/A",  # Insider initial ownership + Amended
    "Form 4",
    "Form 4/A",  # Insider trading report + Amended
    "Form 5",
    "Form 5/A",  # Annual insider ownership changes + Amended
    "424B2",
    "424B3",
    "424B4",
    "424B5",  # Prospectuses (multiple versions)
    "144",
    "144/A",  # Proposed sale of securities + Amended
    "11-K",
    "11-K/A",  # Annual reports of employee stock plans + Amended
    "SD",
    "SD/A",  # Specialized disclosure (e.g., conflict minerals) + Amended
    "N-CSR",
    "N-CSR/A",  # Mutual fund reports + Amended
    "N-Q",
    "N-Q/A",  # Mutual fund quarterly reports + Amended
    "POS AM",  # Post-effective amendment to registration statement
]

DOCLING_MODEL_NAME = "ds4sd/SmolDocling-256M-preview"
PROMPT_TEXT = "Convert page to Docling."
CHAT_TEMPLATE = f"<|im_start|>User:<image>{PROMPT_TEXT}<end_of_utterance>\
Assistant:"
MAX_TOKENS= 8192
PAGE_BREAK = "---Page Break---"