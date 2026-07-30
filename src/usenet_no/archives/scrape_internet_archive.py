import logging
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_page_data(page_url: str, page_data_file: Path, download_again: bool) -> str:
    if not page_data_file.exists() or download_again:
        page = requests.get(page_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        page.raise_for_status()
        page_data_file.parent.mkdir(parents=True, exist_ok=True)
        page_data_file.write_text(page.text)
    return page_data_file.read_text()


def get_urls(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")

    filenames = set()
    for e in soup.find_all("a", href=True):
        href = e["href"]
        if ".zip" not in href:
            continue

        parsed = urlparse(href)
        path = parsed.path if parsed.scheme else href
        filename = Path(unquote(path)).name

        if filename.startswith("no") and filename.endswith(".zip"):
            filenames.add(filename)

    return filenames


def download_zip(url: str, local_filename: Path, retries: int = 5):
    local_filename.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = local_filename.with_suffix(local_filename.suffix + ".part")

    last_error = None

    for attempt in range(1, retries + 1):
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Referer": "https://archive.org/",
            }
        )
        try:
            logger.info("REQUESTING: %s (attempt %d/%d)", url, attempt, retries)
            with session.get(
                url,
                stream=True,
                timeout=60,
                allow_redirects=True,
            ) as response:
                logger.info("FINAL URL:   %s", response.url)
                logger.info("STATUS:      %s", response.status_code)

                if response.status_code in {401, 403, 429, 500, 502, 503, 504}:
                    raise requests.HTTPError(
                        f"{response.status_code} for {response.url}",
                        response=response,
                    )
                response.raise_for_status()

                with tmp_file.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)

            tmp_file.replace(local_filename)
            return True

        except requests.RequestException as e:
            last_error = e
            logger.warning("Download failed: %s", e)

            if tmp_file.exists():
                tmp_file.unlink()

            if attempt < retries:
                wait = min(2**attempt, 30)
                logger.info("Retrying in %d seconds...", wait)
                time.sleep(wait)

    raise last_error
