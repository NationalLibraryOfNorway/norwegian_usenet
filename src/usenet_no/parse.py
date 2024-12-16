from zipfile import ZipFile
from pathlib import Path

def unzip_all(zip_dir: Path, unzip_dir: Path) -> None:
    for zip_file in zip_dir.glob("*.zip"):
        with ZipFile(zip_file, "r") as z:
            z.extractall(unzip_dir)

if __name__ == "__main__":
    zipped_data_dir = Path("data")
    unzipped_data_dir = Path("unzipped_data")
    unzipped_data_dir.mkdir(exist_ok=True)

    if len(list(unzipped_data_dir.iterdir())) != len(list(zipped_data_dir.iterdir())):
        unzip_all(zipped_data_dir, unzipped_data_dir)
