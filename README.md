# Norwegian Usenet


## Data
The data used in this repo comes from two sources: Internet Archive (IA) and **N**asjonal**b**iblioteket (NB, eng:  National Library of Norway).
Because the data may contain personal information, the archives themselves are not shared here.
What we have are scripts to download, extract, and parse the data from both archives, as well as various scripts to analyze the data.
The SQLite databases built from them, one per archive, hold no plain text, and are committed to this repository with git-lfs.

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
    │   ├── ia.db                              # SQLite database of the IA archive, hashes only (scripts/02_build_database/01_build_databases.py)
    │   ├── nb.db                              # SQLite database of the NB archive, hashes only (scripts/02_build_database/01_build_databases.py)
    │   ├── fingerprint_databases.csv          # Hash of every table of each archive, with and without the row ids (scripts/02_build_database/02_fingerprint_databases.py)
    │   └── nb_source_file_counts.csv          # NB source files and nb.db rows per newsgroup (scripts/02_build_database/03_compare_nb_database_against_source_files.py)
    ├── 03_statistics_per_archive/
    ├── 04_compare_message_bodies/
    ├── 05_venn_diagrams/
    ├── 06_graphs_and_references/
    ├── 07_evaluate_embedding_model_robustness/
    ├── 08_make_embeddings/
    └── 09_topic_modelling/
```

### Sqlite databases
`ia.db` and `nb.db` are built from the `utf_8_data` subdirectories, one file per archive, and are what the analysis scripts read.  
They hold names, emails, message ids and bodies only as hashes, so the files can be shared.  
They are stored here with [git-lfs](https://git-lfs.com): with git-lfs installed, `git clone` fetches the files themselves, and `git lfs pull` fetches them in a clone made without them.  
The statistics in step 03, most of the comparisons in step 04, the venn diagrams in step 05, and the graph building scripts in 06 read the two database files and nothing else, so anyone with them can reproduce them.  
The two replacement character scripts in step 04 also read the message bodies from the mbox files, and so need the archives themselves.  
A hash is connected back to its plain text through the mbox files: a message's position in its own file is its row id minus the lowest row id of its newsgroup, in the database of its archive.

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

#### Step 02: building the databases
[01_build_databases.py](scripts/02_build_database/01_build_databases.py) reads every message of an archive into a SQLite database of its own, so that later analyses are SQL queries over the two datasets instead of repeated parses of the archive directories. The databases at `data/output/02_build_database/ia.db` and `data/output/02_build_database/nb.db` store names, emails, message ids and bodies only as hashes, and no free text at all. The scripts that compare the archives read both files at once, through views that name the archive each row came from.

Messages are stored one row per message per newsgroup, with nothing dropped or merged, so the databases are a faithful transcription of the mbox files.

[02_fingerprint_databases.py](scripts/02_build_database/02_fingerprint_databases.py) hashes the rows of both databases, with the row ids and without them, writes the fingerprint to `data/output/02_build_database/`, and prints every value that changed since the last run, which is how databases built on another machine are checked against these. A difference in the ids alone, which is what reading the mbox files in another order gives, is reported as such. See [scripts/02_build_database/README.md](scripts/02_build_database/README.md) for details.

[03_compare_nb_database_against_source_files.py](scripts/02_build_database/03_compare_nb_database_against_source_files.py) counts the NB source files, one per message, behind each newsgroup and compares that against the rows `nb.db` holds for it. Both counts are 613 016 messages, and every one of the 139 newsgroups matches.

#### Step 03: counting messages and users within each archive
Counts messages per newsgroup, user and date in each archive, finds duplicates, conflicting Message-IDs and messages without a sender, and plots those counts. See [scripts/03_statistics_per_archive/README.md](scripts/03_statistics_per_archive/README.md) for details.

#### Step 04: comparing the message bodies of the archives
Compares the IA and NB archives by message body overlap, finds Message-IDs whose copies conflict across the archives, and measures and plots the U+FFFD damage behind those conflicts. See [scripts/04_compare_message_bodies/README.md](scripts/04_compare_message_bodies/README.md) for details.

#### Step 05: venn diagrams
Draws the overlap between the archives as venn diagrams, over newsgroups, users, messages and outward references, with the IA archive restricted to the NB date span. See [scripts/05_venn_diagrams/README.md](scripts/05_venn_diagrams/README.md) for details.

#### Step 06: graphs and references
Builds the edges between newsgroups, from the users they share and the references running between them, and draws the graphs they make, as .html figures and as .gexf files to be opened in Gephi. See [scripts/06_graphs_and_references/README.md](scripts/06_graphs_and_references/README.md) for details.

#### Step 07: evaluate embedding model robustness
Measures how robust an embedding model is to the U+FFFD (`�`) damage in the IA archive, by embedding the damaged IA body and the intact NB body of the same message and comparing them. See [scripts/07_evaluate_embedding_model_robustness/README.md](scripts/07_evaluate_embedding_model_robustness/README.md) for details.

#### Step 08: embed messages
Filters the IA archive to the NB date span, selects newsgroups, makes text embeddings for their messages, reduces them to 2 dimensions with UMAP or t-SNE, and plots them. See [scripts/08_make_embeddings/README.md](scripts/08_make_embeddings/README.md) for details.

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
