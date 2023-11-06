"""A module for a function which scrapes Russell 2000 constituent tickers from a web .pdf file."""

# External imports
import typing
import tempfile
import PyPDF2
import requests

# Module level constants
STRUCTURAL_STRINGS = ["Company", "Ticker"]
JOINT_STRUCTURAL_STRING = " ".join(STRUCTURAL_STRINGS)
URL = "https://content.ftserussell.com/sites/default/files/ru2000_membershiplist_20220624_0.pdf"


def load_russell_2000_tickers() -> typing.List[str]:
    """
    Scrapes Russel 2000 constituent ticker strings from FTSERussell.com
    :return: The list of ticker strings of the Russell 2000 constituents in arbitrary ordering
    """

    # Request target file, raising an error where the response status is anything but 200: OK
    response: requests.Response = requests.get(URL, stream=True, timeout=10)
    if response.status_code != 200:
        raise FileNotFoundError(
            f"Request to Russell ticker specification file returned {response.status_code}"
        )

    # Open a temporary file and write the web response to that file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as local_file:
        local_file.write(response.content)
        local_file.close()

        # Read the temporary file, iterating through the pages and parsing their text
        pdf_reader: PyPDF2.PdfReader = PyPDF2.PdfReader(local_file.name)
        document_tickers: typing.List[str] = []
        for pdf_page in pdf_reader.pages[:-1]:
            # Text other than company names and tickers is discarded
            page_lines: typing.List[str] = pdf_page.extract_text().splitlines()
            candidate_page_lines: typing.List[str] = [
                line for line in page_lines if line not in STRUCTURAL_STRINGS
            ]

            # Parsing may or may not delimit names and tickers with newlines, changing parsing logic
            if candidate_page_lines[0] == JOINT_STRUCTURAL_STRING:
                page_tickers: typing.List[str] = [
                    line.replace(JOINT_STRUCTURAL_STRING, "").split()[-1]
                    for line in candidate_page_lines[1:-3]
                    if line not in STRUCTURAL_STRINGS
                ]
            else:
                page_tickers: typing.List[str] = candidate_page_lines[1:-5:2]

            # Tickers parsed from the page are appended to the document ticker list
            document_tickers: typing.List[str] = document_tickers + page_tickers

        # Destroy the temporary file
        del local_file

    # Return the document tickers collected from the pages
    return document_tickers
