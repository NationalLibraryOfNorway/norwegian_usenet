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

This is the structure of the data directory according to default input/output data cli args 
```
data/
├── input/
│   ├── internet_archive/
│   │   ├── zipped_data/        # Downloaded .zip files from archive.org (scripts/01_extract_and_parse_usenet_data/03_scrape_internet_archive.py)
│   │   ├── unzipped_data/      # Extracted .mbox files (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   ├── utf_8_data/         # UTF-8 encoded .mbox files (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   ├── encodings.json      # Encoding detected per file in unzipped_data (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   └── date_filtered/      # IA messages filtered to the NB date span (scripts/07_make_embeddings/01_filter_internet_archive_by_date.py)
│   └── nb/
│       ├── zipped_data/        # .tar files from the National Library (loaded from multiple CDs)
│       ├── unzipped_data/      # Extracted message files (scripts/01_extract_and_parse_usenet_data/01_extract_nb_archive_and_find_stubbed_newsgroup_names.py)
│       ├── utf_8_data/         # Concatenated .mbox files, UTF-8 encoded (scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py)
│       └── encodings.json      # Encoding detected per file in unzipped_data (scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py)
└── output/                     # Script outputs, one subdirectory per script group
    ├── 01_extract_and_parse_usenet_data/
    ├── 02_build_database/
    │   ├── usenet.db           # Shared SQLite database of both archives, hashes only (scripts/02_build_database.py)
    │   └── usenet_private.db   # Private hash-to-plaintext mapping (scripts/02_build_database.py)
    ├── 03_statistics_per_archive/
    ├── 04_compare_archives/
    ├── 05_venn_diagrams/
    ├── 06_evaluate_embedding_model_robustness/
    ├── 07_make_embeddings/
    ├── 08_newsgroups_and_user_analysis/
    └── 09_visualize/
```

### Sqlite database
The databases are built from the `utf_8_data` subdirectories, and `usenet.db` is what the analysis scripts read.  
The database holds names, emails, message ids and bodies only as hashes, so the file can be shared.  
The statistics in step 03, most of the comparisons in step 04, the venn diagrams in step 05, and the graph building scripts in 08 read `usenet.db` and nothing else, so anyone with the file can reproduce them.  
The two replacement character scripts in step 04 also read the message bodies from the mbox files, and so need the archives themselves.  
`usenet_private.db` maps the hashed names, emails and message ids back to their plain text, so local analysis can connect a hash to the address or to the message body in the mbox files.  
Like the mbox directories, it is not shared.

## Code
`src/usenet_no/` contains core library modules for working with the data. Everything that creates or queries the SQLite databases lives in the `usenet_no.database` submodule.  
`scripts/` contains numbered scripts for processing and analyzing the archives, and script outputs are stored in `data/output/<script group>/`.

## Scripts

The scripts are grouped into subdirectories of the script folder, and are numbered by run order (we run the script with 01_ prefix first, then 02_ etc). Every script can be run with `uv run path-to-script.py`.

#### Step 01: extracting and parsing the data
Extracts the NB tar archives and the IA zip files, and writes both archives as utf-8-encoded .mbox files, one per newsgroup. See [scripts/01_extract_and_parse_usenet_data/README.md](scripts/01_extract_and_parse_usenet_data/README.md) for details.

#### Step 02: building the database
[02_build_database.py](scripts/02_build_database.py) reads every message of both archives into two SQLite databases in one pass, so that later analyses are SQL queries over one dataset instead of repeated parses of the archive directories. The shared database at `data/output/02_build_database/usenet.db` stores names, emails, message ids and bodies only as hashes, and no free text at all; the private database at `data/output/02_build_database/usenet_private.db` maps the hashes back to their plain text.

Messages are stored one row per message per newsgroup, with nothing dropped or merged, so the database is a faithful transcription of the mbox files.

#### Step 03: counting messages and users within each archive
Counts messages per newsgroup, user and date in each archive, and finds duplicates, conflicting Message-IDs and messages without a sender. See [scripts/03_statistics_per_archive/README.md](scripts/03_statistics_per_archive/README.md) for details.

#### Step 04: comparison between archives
Compares the IA and NB archives by message body and Message-ID overlap, and finds Message-IDs whose copies conflict across the archives. See [scripts/04_compare_archives/README.md](scripts/04_compare_archives/README.md) for details.

#### Step 05: venn diagrams
Draws the overlap between the archives as venn diagrams, over newsgroups, users, messages and outward references, with the IA archive restricted to the NB date span. See [scripts/05_venn_diagrams/README.md](scripts/05_venn_diagrams/README.md) for details.

#### Step 06: evaluate embedding model robustness
Measures how robust an embedding model is to the U+FFFD (`�`) damage in the IA archive, by embedding the damaged IA body and the intact NB body of the same message and comparing them. See [scripts/06_evaluate_embedding_model_robustness/README.md](scripts/06_evaluate_embedding_model_robustness/README.md) for details.

#### Step 07: embed messages
Filters the IA archive to the NB date span, selects newsgroups, and makes text embeddings for their messages, reduced to 2 dimensions with UMAP. See [scripts/07_make_embeddings/README.md](scripts/07_make_embeddings/README.md) for details.

#### Step 08: newsgroups and user analysis
Computes user overlap and reference counts between newsgroups, and finds topics with turftopic. See [scripts/08_newsgroups_and_user_analysis/README.md](scripts/08_newsgroups_and_user_analysis/README.md) for details.

#### Step 09: visualize
Plots the statistics, comparisons, embeddings and graphs from the previous steps. See [scripts/09_visualize/README.md](scripts/09_visualize/README.md) for details.

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

Run tests:
```
uv run pytest
```
