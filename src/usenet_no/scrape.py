import argparse

import requests
from bs4 import BeautifulSoup
from pathlib import Path
from tqdm import tqdm


def get_page_data(page_url: str, page_data_file: Path, download_again: bool) -> str:
    if not page_data_file.exists() or download_again:
        page = requests.get(page_url)
        if page.ok:
            with page_data_file.open("w+") as f:
                f.write(page.text)
    return page_data_file.read_text()


def get_urls(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")

    urls = set()
    for e in soup.find_all(
        "a", href=lambda href: href and "no" in href and ".zip" in href
    ):
        urls.add(e.get("href"))
    return urls


def download_zip(url: str, local_filename: Path):
    # Send a GET request to the URL. Use stream=True to enable streaming mode.
    with requests.get(url, stream=True) as response:
        # Check if the request was successful
        response.raise_for_status()

        # Open the local file in binary write mode
        with open(local_filename, "wb") as file:
            # Iterate over the response in chunks
            for chunk in response.iter_content(chunk_size=8192):
                # Write each chunk to the file
                file.write(chunk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Usenet archives")
    parser.add_argument(
        "--page-data",
        type=Path,
        default=Path("data/page_data.txt"),
        help="Location of cached page HTML",
    )
    parser.add_argument(
        "--base-url",
        default="https://archive.org/download/usenet-no",
        help="Usenet archive base URL",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/zipped_data/"),
        help="Directory where zip files are stored",
    )
    parser.add_argument(
        "--download-again",
        action="store_true",
        help="Force re-download of page metadata",
    )
    args = parser.parse_args()

    args.data_dir.mkdir(exist_ok=True)

    page_data = get_page_data(
        page_url=args.base_url,
        page_data_file=args.page_data,
        download_again=args.download_again,
    )
    urls = get_urls(page_data)

    for url in tqdm(urls):
        if url.endswith("/"):
            url = url[:-1]
        zip_url = args.base_url + "/" + url
        local_file = args.data_dir / url
        if not local_file.exists():
            download_zip(zip_url, local_filename=local_file)
