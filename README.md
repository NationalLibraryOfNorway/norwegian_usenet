# Usenet no
A repository for exploring Usenet collections.

The code was developed for a case comparing two collections of Usenet newsgroups: one archived by the National Library of Norway (1994-1997), and the other found in Internet Archive's (ca 1991-2013). However, much of the code is hopefully useful for other cases that needs to fetch and analyse Usenet collections.

For non-computational users, jump to the [ePADD](https://github.com/Sprakbanken/usenet_no#epadd) section.

## Installation

With [uv](https://docs.astral.sh/uv/#installation):  
`uv sync`

With pip and venv:
```
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Data
The data used in this repo comes from two sources: Internet Archive (IA) and **N**asjonal**b**iblioteket (NB, eng:  National Library of Norway).
Because the data may contain personal information, it is not shared here.
What we have are scripts to download, extract, and parse the data from both archives, as well as various scripts to analyze the data.

Assumed file structure once data is downloaded and extracted:
```
data/
├── internet_archive/
│   ├── zipped_data/        # Downloaded .zip files from archive.org (scripts/01_extract_and_parse_usenet_data/02_scrape_internet_archive.py)
│   ├── unzipped_data/      # Extracted .mbox files (scripts/01_extract_and_parse_usenet_data/03_parse_internet_archive.py)
│   ├── utf_8_data/         # UTF-8 encoded .mbox files (scripts/01_extract_and_parse_usenet_data/03_parse_internet_archive.py)
│   └── date_filtered/      # IA messages filtered to the NB date span (scripts/01_extract_and_parse_usenet_data/05_filter_internet_archive_by_date.py)
├── nb/
│   ├── zipped_data/        # .tar files from the National Library
│   ├── unzipped_data/      # Extracted message files (scripts/01_extract_and_parse_usenet_data/01_parse_nb_archive.py)
│   └── utf_8_data/         # Concatenated .mbox files, UTF-8 encoded (scripts/01_extract_and_parse_usenet_data/01_parse_nb_archive.py)
└── usenet.db               # SQLite database of both archives (scripts/02_build_database.py)
```
The database is built from the `utf_8_data` subdirectories and is what the analysis scripts read. It holds each sender's name and email both in plain text and hashed, so statistics can be published by hash while local analysis still has the address. Like the mbox directories, it is not shared.

## Code
`src/usenet_no/` contains core library modules for working with mbox data.  
`scripts/` contains standalone scripts for reading through the archives and generating statistics. Output is stored in `data/`.  
`notebooks/` contains Jupyter notebooks for visualizing and interpreting results from the scripts.

## Scripts

The scripts are grouped into subdirectories of the script folder, and are numbered by run order (we run the script with 01_ prefix first, then 02_ etc). Every script can be run with `uv run path-to-script.py`.

#### Step 01: extracting and parsing the data
The scripts for preparing the data for analysis live in `scripts/01_extract_and_parse_usenet_data`.  

- [01_parse_nb_archive.py](scripts/01_extract_and_parse_usenet_data/01_parse_nb_archive.py) reads the data as it was stored on the CDs in the NB deposit, and write one utf-8-encoded .mbox file per newsgroup
- [02_scrape_internet_archive.py](scripts/01_extract_and_parse_usenet_data/02_scrape_internet_archive.py) fetches and downloads all zip files from `https://archive.org/download/usenet-no` (stored in `data/internet_archive/zipped_data` by default).  
- [03_parse_internet_archive.py](scripts/01_extract_and_parse_usenet_data/03_parse_internet_archive.py) unzips and reads all mbox files from the scrape output. Files are decoded and re-encoded to UTF-8 and written to `data/internet_archive/utf_8_data`.
- [05_filter_internet_archive_by_date.py](scripts/01_extract_and_parse_usenet_data/05_filter_internet_archive_by_date.py) filters the IA mbox files to only include messages within the date span of the NB archive (reading `data/date_count_nb.csv`), and writes them to `data/internet_archive/date_filtered`. Messages whose date could not be parsed are kept.

The date filtered copy exists because the comparison scripts in step 04 read the mbox files rather than the database: comparing message bodies needs the text itself, which the database stores only as a hash.

#### Step 02: building the database

[02_build_database.py](scripts/02_build_database.py) reads every message of both archives into a SQLite database at `data/usenet.db`, so that later analyses are SQL queries over one dataset instead of repeated parses of the archive directories. Restricting the Internet Archive to the date span of the NB archive is a `WHERE` clause on this database, rather than a filtered copy on disk.

Messages are stored one row per message per newsgroup, with nothing dropped or merged, so the database is a faithful transcription of the mbox files. Message bodies are stored as hashes only.

#### Step 03: counting messages and users in each archive 

Every script here reads `data/usenet.db`, except the duplicate count, which reads the mbox files directly so that it stays independent of the data it is used to check. Where a statistic is reported for the date filtered IA archive, that is a `WHERE` clause restricting IA to the NB date span, not a separate copy of the data.

- [01_count_messages_per_group.py](scripts/03_statistics_per_archive/01_count_messages_per_group.py) counts messages per newsgroup for each of IA, date filtered IA and NB archives. Creates `data/messages_per_group_ia.csv`, `data/messages_per_group_ia_date_filtered.csv`  and `data/messages_per_group_nb.csv`
- [02_count_duplicate_messages.py](scripts/03_statistics_per_archive/02_count_duplicate_messages.py) finds *true duplicates*: messages stored more than once in the same mbox file with both the same Message-ID and the same body. Creates `data/duplicate_messages_per_group.jsonl`, with one row per duplicated Message-ID (`source_archive`, `newsgroup`, `message_id`, `count`), where `count` is the total number of copies present.
- [03_count_messages_per_user.py](scripts/03_statistics_per_archive/03_count_messages_per_user.py) counts messages per user, reported by the hashes the database already holds, so no plain text name or email is written out. Creates `data/messages_per_user_ia.csv`, `data/messages_per_user_ia_date_filtered.csv` and `data/messages_per_user_nb.csv`. Messages with no sender are left out, and counted by `06_count_messages_without_sender.py` instead.
- [04_count_messages_per_date.py](scripts/03_statistics_per_archive/04_count_messages_per_date.py) counts messages per date in each of IA and NB archives. Messages whose date could not be parsed are reported in a row labelled `unknown`. Outputs one file for each archive: `data/date_count_ia.csv` and `data/date_count_nb.csv`
- [06_count_messages_without_sender.py](scripts/03_statistics_per_archive/06_count_messages_without_sender.py) counts messages that carry no From header, and whose sender is therefore unknown, per archive and newsgroup. Creates `data/messages_without_sender.jsonl`.

#### Step 04: comparing archives
(more to come)

- (00_compare_ia_nb_message_content.py)[scripts/04_compare_archives/00_compare_ia_nb_message_content.py] compares message body overlap between IA and NB by exact text match, per newsgroup. Creates `data/ia_nb_content_comparison.csv` and `data/ia_nb_content_comparison_date_filtered.csv` 
- (00_compare_ia_nb_message_ids.py)[scripts/04_compare_archives/00_compare_ia_nb_message_ids.py] compares message-ID overlap between IA and NB, and collects external references. Creates `data/ia_nb_message_id_overlap.json` and `data/ia_nb_message_id_overlap_date_filtered.json`

#### Step 05: embed messages

(01_embed_messages.py)[scripts/05_make_embeddings/01_embed_messages.py] - makes text embeddings for each message in each newsgroup (from a selection of newsgroups) from both archives. 

#### Step 06: topic modelling 

(06_topic_modelling.py)[scripts/06_topic_modelling.py] - uses BERTopic and the text embeddings generated in the previous step to find topics in the selected newsgroups


#### Step 07: visualize

- [00_newsgroup_tree.py](scripts/07_visualize/00_newsgroup_tree.py) draws the nested newsgroup structure of each archive as an ASCII tree, reading `data/messages_per_group_ia.csv` and `data/messages_per_group_nb.csv` (from step 03). Prints to stdout.
- [00_newsgroup_tree_gif.py](scripts/07_visualize/00_newsgroup_tree_gif.py) draws the same trees as scrolling animations. Creates `data/newsgroup_tree_ia.gif` and `data/newsgroup_tree_nb.gif`
- [00_visualize_embeddings.py](scripts/07_visualize/00_visualize_embeddings.py) plots the UMAP embeddings from step 05 as an interactive Plotly scatter plot, coloured by newsgroup and shaped by archive. Opens in a browser.
- [00_visualize_topics.py](scripts/07_visualize/00_visualize_topics.py) plots the same UMAP embeddings coloured by the BERTopic topics from step 06. Opens in a browser.


## ePADD
ePADD is a program with a graphical interface for exploring email archives.
Since the Usenet archive is stored as .mbox files, it can be explored with ePADD.

Download the .jar file from https://github.com/ePADD/epadd/releases/  
(filename: epadd-standalone.jar) and move it here.

Requires Java:
```
java -jar epadd-standalone.jar
```

### NB-epadd
Read about NB-epadd here: https://github.com/NationalLibraryOfNorway/epadd-nb  
(Requires entity extraction outside of epadd — see the README in that repo.)

## For developers

### Pre-commit
Install pre-commit hooks (first time):
```
uv run pre-commit install
```
This runs the hooks defined in `.pre-commit-config.yaml` on every commit.

### Tests
Tests mirror the directory structure in `src/`, with one file per function being tested.
At the deepest level, a `.py` file in `src/` corresponds to a directory in `tests/`, with one `test_<function_name>.py` file per function in that source file.

Run tests:
```
uv run pytest
```
