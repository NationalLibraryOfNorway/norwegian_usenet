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
│   ├── zipped_data/        # Downloaded .zip files from archive.org (scripts/extract_and_parse_usenet_data/scrape_internet_archive.py)
│   ├── unzipped_data/      # Extracted .mbox files (scripts/extract_and_parse_usenet_data/parse_internet_archive.py)
│   ├── utf_8_data/         # UTF-8 encoded .mbox files (scripts/extract_and_parse_usenet_data/parse_internet_archive.py)
│   └── date_filtered/      # IA messages filtered to the NB date span (scripts/extract_and_parse_usenet_data/filter_internet_archive_by_date.py)
├── nb/
│   ├── zipped_data/        # .tar files from the National Library
│   ├── unzipped_data/      # Extracted message files (scripts/extract_and_parse_usenet_data/parse_norwegian_web_archive.py)
│   └── utf_8_data/         # Concatenated .mbox files, UTF-8 encoded (scripts/extract_and_parse_usenet_data/parse_norwegian_web_archive.py)
└── hidden/                 # Mappings from email and name to hash values (src/usenet_no/make_user_mapping.py)
```
(Analysis scripts only use the `utf_8_data` subdirectories, or `date_filtered` for date-filtered IA analysis.)

## Code
`src/usenet_no/` contains core library modules for working with mbox data.  
`scripts/` contains standalone scripts for reading through the archives and generating statistics. Output is stored in `data/`.  
`notebooks/` contains Jupyter notebooks for visualizing and interpreting results from the scripts.

### Scripts

The scripts are grouped into subdirectories of the script folder, and are numbered by run order (we run the script with 01_ prefix first, then 02_ etc). Every script can be run with `uv run path-to-script.py`.

#### Step 01: extracting and parsing the data
The scripts for preparing the data for analysis live in `scripts/01_extract_and_parse_usenet_data`.  

- [01_parse_nb_archive.py](scripts/01_extract_and_parse_usenet_data/01_parse_nb_archive.py) reads the data as it was stored on the CDs in the NB deposit, and write one utf-8-encoded .mbox file per newsgroup
- [02_scrape_internet_archive.py](scripts/01_extract_and_parse_usenet_data/02_scrape_internet_archive.py) fetches and downloads all zip files from `https://archive.org/download/usenet-no` (stored in `data/internet_archive/zipped_data` by default).  
- [03_parse_internet_archive.py](scripts/01_extract_and_parse_usenet_data/03_parse_internet_archive.py) unzips and reads all mbox files from the scrape output. Files are decoded and re-encoded to UTF-8 and written to `data/internet_archive/utf_8_data`.
- [04_parse_date_fields_in_both_archives.py](scripts/01_extract_and_parse_usenet_data/04_parse_date_fields_in_both_archives.py) parses the date header of each message, and counts messages per date in each of IA and NB archives. Outputs one file for each archive: `data/date_count_ia.csv` and `data/date_count_nb.csv`
- [05_filter_internet_archive_by_date.py](scripts/01_extract_and_parse_usenet_data/05_filter_internet_archive_by_date.py) filters the IA mbox files to only include messages within the date span of the NB archive (reading `data/date_count_nb.csv`), and writes them to `data/internet_archive/date_filtered`.

It's the date filtered version of the internet archive that is used for most of the comparison analysis.

#### Step 02: counting messages and users in each archive 

- [01_count_messages_per_group.py](scripts/02_statistics_per_archive/01_count_messages_per_group.py) counts messages per newsgroup (i.e. mbox file) for each of IA, date filtered IA and NB archives. Creates `data/messages_per_group_ia.csv`, `data/messages_per_group_ia_date_filtered.csv`  and `data/messages_per_group_nb.csv`
- [02_hash_user_emails_and_names.py](scripts/02_statistics_per_archive/02_hash_user_emails_and_names.py) creates a mapping from email addresses and names in plain text to hashed values. This way, we can store output data files on GitHub,  without them containing names and email addresses. 
- [03_count_messages_per_user.py](scripts/02_statistics_per_archive/03_count_messages_per_user.py) counts messages per user (anonymized with hash). Creates `data/messages_per_user_ia.csv`, `data/messages_per_user_ia_date_filtered.csv` and `data/messages_per_user_nb.csv`.

#### Step 03: comparing archives
(more to come)

- (01_compare_ia_nb_message_content.py)[scripts/03_compare_archives/01_compare_ia_nb_message_content.py] compares message body overlap between IA and NB by exact text match, per newsgroup. Creates `data/ia_nb_content_comparison.csv` and `data/ia_nb_content_comparison_date_filtered.csv` 
- (01_compare_ia_nb_message_ids.py)[scripts/03_compare_archives/01_compare_ia_nb_message_ids.py] compares message-ID overlap between IA and NB, and collects external references. Creates `data/ia_nb_message_id_overlap.json` and `data/ia_nb_message_id_overlap_date_filtered.json`


**Visualization:**
- `scripts/newsgroup_tree.py` — generates an ASCII visualization of the nested newsgroup structure. Output: printed to stdout.
- `scripts/newsgroup_tree_gif.py` — generates animated GIF visualizations of the newsgroup structure. Output: `data/newsgroup_tree_ia.gif` / `data/newsgroup_tree_nb.gif`
- `scripts/export_umap_for_web.py` — exports UMAP embedding data for the GitHub Pages visualization. Output: `docs/data/`


### Embedding scripts
Scripts for embedding messages are located in `scripts/embed_messages/`:
- `embed_top_n.py` — embeds the top N most active newsgroups
- `embed_n_median.py` — embeds N newsgroups around the median activity level
- `embed_n_closest_to_k.py` — embeds N newsgroups closest to a given size k
- `embed_selection.py` — embeds a configurable selection of newsgroups (defined in `data/newsgroups_for_selection.jsonl`)

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
