from zipfile import ZipFile
from pathlib import Path
import re
import base64
import quopri
import email
from mailbox import mbox
from collections import Counter
import argparse
import cchardet as chardet
from tqdm import tqdm
import json


def get_text_content(part: email.message.Message) -> str:
    content = part._payload
    headers = dict(part._headers)
    if "charset" in headers["Content-Type"]:
        bits = headers["Content-Type"].split("charset=")
        if bits[1].startswith('"'):
            charset = bits[1].split('"')[1]
        else:
            charset = re.split(r"\s", bits[1])[0]
    if "Content-Transfer-Encoding" in headers:
        match headers["Content-Transfer-Encoding"]:
            case "quoted-printable":
                content = quopri.decodestring(content).decode(charset)
            case "base64":
                content = base64.b64decode(content).decode(charset)
            case "8bit":
                content = content.encode(charset, "surrogateescape").decode("utf-8")
            case _:
                print(headers)
    return content


def get_text_messages(box: mbox) -> dict[str, list[email.message.Message]]:
    # TODO: This only works is there is no more than 1 text/plain part per message-id...
    messages = {}
    multi_part = 0
    single_part = 0
    for msg in box:
        # print(len(msg))
        msg_id = msg["message-id"].strip()
        # print(f"Message-ID {msg_id}" )
        if msg.is_multipart():
            multi_part += 1

            for i, part in enumerate(msg.walk()):
                if part.get_content_type() == "text/plain":
                    messages[msg_id] = part
                else:
                    print("not text/plain")
                    print(part.get_content_type())
            # print(f"Num parts multipart {i}")
        else:
            single_part += 1
            if msg.get_content_type() == "text/plain":
                messages[msg_id] = msg
            else:
                print("not text/plain")

    # print(f"Multi-part messages: {multi_part}\nSingle-part messages: {single_part}")
    return messages


def count_content_types(box: mbox) -> dict[str, int]:
    content_types = Counter()
    for msg in box:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_types[content_type] += 1

        content_type = msg.get_content_type()
        content_types[content_type] += 1
    return content_types


def get_text_contents(box: mbox) -> dict[str, str]:
    return {k: get_text_content(msg) for k, msg in get_text_messages(box).items()}


def unzip_all(zip_dir: Path, unzip_dir: Path) -> None:
    for zip_file in zip_dir.glob("*.zip"):
        with ZipFile(zip_file, "r") as z:
            z.extractall(unzip_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse and process Usenet mbox data")
    parser.add_argument(
        "--zipped-data-dir",
        type=Path,
        default=Path("data/zipped_data"),
        help="Directory containing zipped mbox files",
    )
    parser.add_argument(
        "--unzipped-data-dir",
        type=Path,
        default=Path("data/unzipped_data"),
        help="Directory to store unzipped mbox files",
    )
    parser.add_argument(
        "--encodings-file",
        type=Path,
        default=Path("data/encodings.json"),
        help="Path to JSON file storing detected encodings",
    )
    args = parser.parse_args()

    zipped_data_dir = args.zipped_data_dir
    unzipped_data_dir = args.unzipped_data_dir
    encodings_file = args.encodings_file
    unzipped_data_dir.mkdir(exist_ok=True)

    if len(list(unzipped_data_dir.iterdir())) != len(list(zipped_data_dir.iterdir())):
        unzip_all(zipped_data_dir, unzipped_data_dir)

    if encodings_file.exists():
        with encodings_file.open() as f:
            files_encodings = json.load(f)
    else:
        files_encodings = {}

    print(files_encodings.keys())

    for mbox_file in tqdm(
        unzipped_data_dir.iterdir(), total=len(list(unzipped_data_dir.iterdir()))
    ):
        if mbox_file.stem in files_encodings:
            continue
        try:
            [e for e in mbox(mbox_file)]
            files_encodings[mbox_file.stem] = {"encoding": "utf-8"}

        except Exception:
            detection = chardet.detect(mbox_file.read_bytes())
            files_encodings[mbox_file.stem] = chardet.detect(mbox_file.read_bytes())

        with encodings_file.open("w+") as f:
            json.dump(files_encodings, fp=f, indent=4)
        # content_types = count_content_types(mbox(mbox_file))
        # print(content_types)
