# Norwegian Usenet


## Data
The data used in this repo comes from two sources: Internet Archive (IA) and **N**asjonal**b**iblioteket (NB, eng:  National Library of Norway).
Because the data may contain personal information, the archives themselves are not shared here.
What we have are scripts to download, extract, and parse the data from both archives, as well as various scripts to analyze the data.
The SQLite database built from them holds no plain text, and is committed to this repository with git-lfs.

This is the structure of the data directory according to default input/output data cli args 
```
data/
├── input/
│   ├── internet_archive/
│   │   ├── zipped_data/        # Downloaded .zip files from archive.org (scripts/01_extract_and_parse_usenet_data/03_scrape_internet_archive.py)
│   │   ├── unzipped_data/      # Extracted .mbox files (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   ├── utf_8_data/         # UTF-8 encoded .mbox files (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   └── encodings.json      # Encoding detected per file in unzipped_data (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   └── nb/
│       ├── zipped_data/        # .tar files from the National Library (loaded from multiple CDs)
│       ├── unzipped_data/      # Extracted message files (scripts/01_extract_and_parse_usenet_data/01_extract_nb_archive_and_find_stubbed_newsgroup_names.py)
│       ├── utf_8_data/         # Concatenated .mbox files, UTF-8 encoded (scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py)
│       └── encodings.json      # Encoding detected per file in unzipped_data (scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py)
└── output/                     # Script outputs, one subdirectory per script group
    ├── 01_extract_and_parse_usenet_data/
    ├── 02_build_database/
    │   ├── usenet.db                             # SQLite database of both archives, hashes only (scripts/02_build_database/01_build_database.py)
    │   ├── fingerprint_database.csv              # Hash of every table, row ids included (scripts/02_build_database/02_fingerprint_database.py)
    │   ├── fingerprint_database_content.csv      # The same with the row ids left out (scripts/02_build_database/03_fingerprint_database_content.py)
    │   └── fingerprint_database_per_archive.csv  # The same split by archive (scripts/02_build_database/04_fingerprint_database_per_archive.py)
    ├── 03_statistics_per_archive/
    ├── 04_compare_message_bodies/
    ├── 05_venn_diagrams/
    ├── 06_graphs_and_references/
    ├── 07_evaluate_embedding_model_robustness/
    ├── 08_make_embeddings/
    └── 09_topic_modelling/
```

### Sqlite database
`usenet.db` is built from the `utf_8_data` subdirectories, and is what the analysis scripts read.  
The database holds names, emails, message ids and bodies only as hashes, so the file can be shared.  
It is stored here with [git-lfs](https://git-lfs.com): with git-lfs installed, `git clone` fetches the file itself, and `git lfs pull` fetches it in a clone made without it.  
The statistics in step 03, most of the comparisons in step 04, the venn diagrams in step 05, and the graph building scripts in 06 read `usenet.db` and nothing else, so anyone with the file can reproduce them.  
The two replacement character scripts in step 04 also read the message bodies from the mbox files, and so need the archives themselves.  
A hash is connected back to its plain text through the mbox files: a message's position in its own file is its row id minus the lowest row id of its (archive, newsgroup).

## Install dependencies

With [uv](https://docs.astral.sh/uv/#installation):  
`uv sync`


## Code
`src/usenet_no/` contains core library modules for working with the data. Everything that creates or queries the SQLite databases lives in the `usenet_no.database` submodule.  
`scripts/` contains numbered scripts for processing and analyzing the archives, and script outputs are stored in `data/output/<script group>/`.

## Scripts

The scripts are grouped into subdirectories of the script folder, and are numbered by run order (we run the script with 01_ prefix first, then 02_ etc). Every script can be run with `uv run path-to-script.py`.

#### Step 01: extracting and parsing the data
Extracts the NB tar archives and the IA zip files, and writes both archives as utf-8-encoded .mbox files, one per newsgroup. See [scripts/01_extract_and_parse_usenet_data/README.md](scripts/01_extract_and_parse_usenet_data/README.md) for details.

#### Step 02: building the database
[01_build_database.py](scripts/02_build_database/01_build_database.py) reads every message of both archives into one SQLite database in a single pass, so that later analyses are SQL queries over one dataset instead of repeated parses of the archive directories. The database at `data/output/02_build_database/usenet.db` stores names, emails, message ids and bodies only as hashes, and no free text at all.

Messages are stored one row per message per newsgroup, with nothing dropped or merged, so the database is a faithful transcription of the mbox files.

The three fingerprint scripts hash the rows of a database, write the fingerprint to `data/output/02_build_database/`, and print every value that changed since the last run, which is how a database built on another machine is checked against this one. See [scripts/02_build_database/README.md](scripts/02_build_database/README.md) for details.

#### Step 03: counting messages and users within each archive
Counts messages per newsgroup, user and date in each archive, finds duplicates, conflicting Message-IDs and messages without a sender, and plots those counts. See [scripts/03_statistics_per_archive/README.md](scripts/03_statistics_per_archive/README.md) for details.

#### Step 04: comparing the message bodies of the archives
Compares the IA and NB archives by message body overlap, finds Message-IDs whose copies conflict across the archives, and measures and plots the U+FFFD damage behind those conflicts. See [scripts/04_compare_message_bodies/README.md](scripts/04_compare_message_bodies/README.md) for details.

#### Step 05: venn diagrams
Draws the overlap between the archives as venn diagrams, over newsgroups, users, messages and outward references, with the IA archive restricted to the NB date span. See [scripts/05_venn_diagrams/README.md](scripts/05_venn_diagrams/README.md) for details.

#### Step 06: graphs and references
Builds the edges between newsgroups, from the users they share and the references running between them, and draws the graphs they make. See [scripts/06_graphs_and_references/README.md](scripts/06_graphs_and_references/README.md) for details.

#### Step 07: evaluate embedding model robustness
Measures how robust an embedding model is to the U+FFFD (`�`) damage in the IA archive, by embedding the damaged IA body and the intact NB body of the same message and comparing them. See [scripts/07_evaluate_embedding_model_robustness/README.md](scripts/07_evaluate_embedding_model_robustness/README.md) for details.

#### Step 08: embed messages
Filters the IA archive to the NB date span, selects newsgroups, makes text embeddings for their messages, reduces them to 2 dimensions with UMAP, and plots them. See [scripts/08_make_embeddings/README.md](scripts/08_make_embeddings/README.md) for details.

#### Step 09: topic modelling
Finds topics in one newsgroup with turftopic, over the embeddings from the previous step, and plots the messages coloured by topic. See [scripts/09_topic_modelling/README.md](scripts/09_topic_modelling/README.md) for details.


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
