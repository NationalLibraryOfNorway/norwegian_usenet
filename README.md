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
├── input/
│   ├── internet_archive/
│   │   ├── zipped_data/        # Downloaded .zip files from archive.org (scripts/01_extract_and_parse_usenet_data/03_scrape_internet_archive.py)
│   │   ├── unzipped_data/      # Extracted .mbox files (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   ├── utf_8_data/         # UTF-8 encoded .mbox files (scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py)
│   │   └── date_filtered/      # IA messages filtered to the NB date span (scripts/05_make_embeddings/01_filter_internet_archive_by_date.py)
│   └── nb/
│       ├── zipped_data/        # .tar files from the National Library (loaded from multiple CDs)
│       ├── unzipped_data/      # Extracted message files (scripts/01_extract_and_parse_usenet_data/01_extract_nb_archive_and_find_stubbed_newsgroup_names.py)
│       └── utf_8_data/         # Concatenated .mbox files, UTF-8 encoded (scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py)
└── output/                     # Script outputs, one subdirectory per script group
    ├── 01_extract_and_parse_usenet_data/
    ├── 02_build_database/
    │   ├── usenet.db           # Shared SQLite database of both archives, hashes only (scripts/02_build_database.py)
    │   └── usenet_private.db   # Private hash-to-plaintext mapping (scripts/02_build_database.py)
    ├── 03_statistics_per_archive/
    ├── 04_compare_archives/
    ├── 05_make_embeddings/
    ├── 06_topic_modelling/
    └── 07_visualize/
```
The databases are built from the `utf_8_data` subdirectories, and `usenet.db` is what the analysis scripts read. It holds names, emails, message ids and bodies only as hashes, so the file can be shared. The statistics and comparisons in steps 03 and 04 read `usenet.db` and nothing else, so anyone with the file can reproduce them. `usenet_private.db` maps the hashed names, emails and message ids back to their plain text, so local analysis can connect a hash to the address or to the message body in the mbox files. Like the mbox directories, it is not shared.

## Code
`src/usenet_no/` contains core library modules for working with mbox data. Everything that creates or queries the SQLite databases lives in the `usenet_no.database` package.  
`scripts/` contains standalone scripts for reading through the archives and generating statistics. Output is stored in `data/output/<script group>/`.

## Scripts

The scripts are grouped into subdirectories of the script folder, and are numbered by run order (we run the script with 01_ prefix first, then 02_ etc). Every script can be run with `uv run path-to-script.py`.

#### Step 01: extracting and parsing the data
The scripts for preparing the data for analysis live in `scripts/01_extract_and_parse_usenet_data`.  

- [01_extract_nb_archive_and_find_stubbed_newsgroup_names.py](scripts/01_extract_and_parse_usenet_data/01_extract_nb_archive_and_find_stubbed_newsgroup_names.py) extracts the NB tar archives to `data/input/nb/unzipped_data`, then finds newsgroup names the KZ2001-0147 CD cut off to 8 characters (8.3 file naming), by matching them against the other NB sources' names at the same position in the newsgroup tree. Writes the pairs to `data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv`, which is meant to be reviewed before running the next script and can carry hand-added rows.
- [02_parse_nb_archive.py](scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py) reads the extracted NB data and writes one utf-8-encoded .mbox file per newsgroup. Newsgroup names listed in `data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv` are replaced when building the mbox filenames, so messages from a cut-off directory land in the same file as the sources that carry the full name.
- [03_scrape_internet_archive.py](scripts/01_extract_and_parse_usenet_data/03_scrape_internet_archive.py) fetches and downloads all zip files from `https://archive.org/download/usenet-no` (stored in `data/input/internet_archive/zipped_data` by default).  
- [04_parse_internet_archive.py](scripts/01_extract_and_parse_usenet_data/04_parse_internet_archive.py) unzips and reads all mbox files from the scrape output. Files are decoded and re-encoded to UTF-8 and written to `data/input/internet_archive/utf_8_data`.

#### Step 02: building the database

[02_build_database.py](scripts/02_build_database.py) reads every message of both archives into two SQLite databases in one pass, so that later analyses are SQL queries over one dataset instead of repeated parses of the archive directories. The shared database at `data/output/02_build_database/usenet.db` stores names, emails, message ids and bodies only as hashes, and no free text at all; the private database at `data/output/02_build_database/usenet_private.db` maps the hashes back to their plain text.

Messages are stored one row per message per newsgroup, with nothing dropped or merged, so the database is a faithful transcription of the mbox files.

#### Step 03: counting messages and users in each archive 

Every script here reads `data/output/02_build_database/usenet.db`. Where a statistic is reported for the date filtered IA archive, that is a `WHERE` clause restricting IA to the NB date span, not a separate copy of the data.

- [01_count_messages_per_group.py](scripts/03_statistics_per_archive/01_count_messages_per_group.py) counts messages per newsgroup for each of IA, date filtered IA and NB archives. Creates `data/output/03_statistics_per_archive/messages_per_group_ia.csv`, `data/output/03_statistics_per_archive/messages_per_group_ia_date_filtered.csv`  and `data/output/03_statistics_per_archive/messages_per_group_nb.csv`
- [02_count_duplicate_messages.py](scripts/03_statistics_per_archive/02_count_duplicate_messages.py) finds *true duplicates*: messages stored more than once in the same mbox file with both the same Message-ID and the same body. Every copy is its own row in the database, so these are rows sharing archive, newsgroup, hashed Message-ID and hashed body. Creates `data/output/03_statistics_per_archive/duplicate_messages_per_group.jsonl`, with one row per duplicated Message-ID (`source_archive`, `newsgroup`, `hashed_message_id`, `count`), where `count` is the total number of copies present.
- [03_count_messages_per_user.py](scripts/03_statistics_per_archive/03_count_messages_per_user.py) counts messages per user, reported by the hashes the database already holds, so no plain text name or email is written out. Creates `data/output/03_statistics_per_archive/messages_per_user_ia.csv`, `data/output/03_statistics_per_archive/messages_per_user_ia_date_filtered.csv` and `data/output/03_statistics_per_archive/messages_per_user_nb.csv`. Messages with no sender are left out, and counted by `06_count_messages_without_sender.py` instead.
- [04_count_messages_per_date.py](scripts/03_statistics_per_archive/04_count_messages_per_date.py) counts messages per date in each of IA and NB archives. Messages whose date could not be parsed are reported in a row labelled `unknown`. Outputs one file for each archive: `data/output/03_statistics_per_archive/date_count_ia.csv` and `data/output/03_statistics_per_archive/date_count_nb.csv`
- [05_find_conflicting_message_ids.py](scripts/03_statistics_per_archive/05_find_conflicting_message_ids.py) finds Message-IDs that carry more than one distinct body *within* a single archive, i.e. messages that cannot be deduplicated on Message-ID without losing a version. Creates `data/output/03_statistics_per_archive/conflicting_message_ids_within_archive.jsonl`.
- [06_count_messages_without_sender.py](scripts/03_statistics_per_archive/06_count_messages_without_sender.py) counts messages that carry no From header, and whose sender is therefore unknown, per archive and newsgroup. Creates `data/output/03_statistics_per_archive/messages_without_sender.jsonl`.

#### Step 04: comparing archives

These scripts all read `data/output/02_build_database/usenet.db`. The scripts are unnumbered (all with a `00_` prefix) because they are independent of each other and can be run in any order.

- [00_compare_ia_nb_message_content.py](scripts/04_compare_archives/00_compare_ia_nb_message_content.py) compares message body overlap between IA and NB by exact text match, per newsgroup. Creates `data/output/04_compare_archives/ia_nb_content_comparison.csv` and `data/output/04_compare_archives/ia_nb_content_comparison_date_filtered.csv`
- [00_compare_ia_nb_message_ids.py](scripts/04_compare_archives/00_compare_ia_nb_message_ids.py) compares message-ID overlap between IA and NB, and collects external references. Creates `data/output/04_compare_archives/ia_nb_message_id_overlap.json`, `data/output/04_compare_archives/ia_nb_message_id_overlap_date_filtered.json`, `data/output/04_compare_archives/ia_nb_message_id_comparison.csv` and `data/output/04_compare_archives/ia_nb_message_id_comparison_date_filtered.csv`
- [00_find_conflicting_message_ids_across_archives.py](scripts/04_compare_archives/00_find_conflicting_message_ids_across_archives.py) finds Message-IDs held by both archives whose copies never agree on a body. Creates `data/output/04_compare_archives/conflicting_message_ids_across_archives.jsonl`.

#### Step 05: embed messages

These scripts read the mbox files rather than the database, since embedding needs the message text itself, which the database stores only as a hash.

- [00_select_newsgroups.py](scripts/05_make_embeddings/00_select_newsgroups.py) writes the top 50 newsgroups by combined unique message count, reading `data/output/04_compare_archives/ia_nb_content_comparison_date_filtered.csv` (from step 04) and keeping only groups where both archives contribute unique messages. Creates `data/output/05_make_embeddings/newsgroups_for_selection.jsonl`, meant as candidates when choosing the `--selection` newsgroups for the scripts below.
- [01_filter_internet_archive_by_date.py](scripts/05_make_embeddings/01_filter_internet_archive_by_date.py) filters the IA mbox files to only include messages within the date span of the NB archive (reading `data/output/03_statistics_per_archive/date_count_nb.csv`), and writes them to `data/input/internet_archive/date_filtered`. Messages whose date could not be parsed are kept.
- [02_embed_messages.py](scripts/05_make_embeddings/02_embed_messages.py) makes text embeddings for each message in a selection of newsgroups from both archives, with a sentence-transformers model. Writes to `data/output/05_make_embeddings/<model>/`.
- [02_make_jina_embeddings.py](scripts/05_make_embeddings/02_make_jina_embeddings.py) does the same with a Jina embedding model. It is an alternative to `02_embed_messages.py`, hence the same number prefix — run one or the other.
- [03_umap_reduce_embeddings.py](scripts/05_make_embeddings/03_umap_reduce_embeddings.py) reduces the embeddings to 2 dimensions with UMAP, and caches the result in `data/output/05_make_embeddings/umap_embeddings/<model>/`.

#### Step 06: topic modelling 

[06_topic_modelling.py](scripts/06_topic_modelling.py) uses BERTopic and the text embeddings generated in the previous step to find topics in the selected newsgroups


#### Step 07: visualize

- [00_newsgroup_tree.py](scripts/07_visualize/00_newsgroup_tree.py) draws the nested newsgroup structure of each archive as an ASCII tree, reading `data/output/03_statistics_per_archive/messages_per_group_ia.csv` and `data/output/03_statistics_per_archive/messages_per_group_nb.csv` (from step 03). Prints to stdout.
- [00_newsgroup_tree_gif.py](scripts/07_visualize/00_newsgroup_tree_gif.py) draws the same trees as scrolling animations. Creates `data/output/07_visualize/newsgroup_tree_gif/newsgroup_tree_ia.gif` and `data/output/07_visualize/newsgroup_tree_gif/newsgroup_tree_nb.gif`
- [00_visualize_embeddings.py](scripts/07_visualize/00_visualize_embeddings.py) plots the UMAP embeddings from step 05 as an interactive Plotly scatter plot, coloured by newsgroup and shaped by archive. Opens in a browser.
- [00_visualize_topics.py](scripts/07_visualize/00_visualize_topics.py) plots the same UMAP embeddings coloured by the BERTopic topics from step 06. Opens in a browser.
- [00_plot_date_counts.py](scripts/07_visualize/00_plot_date_counts.py) plots message counts over time (daily, monthly and yearly) for each archive, reading the `date_count_*.csv` files from step 03. Saves .png files to `data/output/07_visualize/plot_date_counts/`.
- [00_plot_messages_per_group.py](scripts/07_visualize/00_plot_messages_per_group.py) plots newsgroup overlap between the archives, messages in the top 20 groups vs the rest, and the distribution of newsgroups by message count, reading the `messages_per_group_*.csv` files from step 03. Prints group statistics to stdout and saves .png files to `data/output/07_visualize/plot_messages_per_group/`.
- [00_plot_messages_per_user.py](scripts/07_visualize/00_plot_messages_per_user.py) plots posts by the top 100 users vs the rest, the cumulative post distribution by user, and user overlap between the archives, reading the `messages_per_user_*.csv` files from step 03. Prints user statistics to stdout and saves image files to `data/output/07_visualize/plot_messages_per_user/`.
- [00_plot_ia_nb_content_comparison.py](scripts/07_visualize/00_plot_ia_nb_content_comparison.py) plots exact-body-match message overlap between IA and NB, reading the `ia_nb_content_comparison*.csv` files from step 04. Prints overlap statistics to stdout and saves `content_overlap_venn.png` to `data/output/07_visualize/plot_ia_nb_content_comparison/`.
- [00_plot_ia_nb_message_id_overlap.py](scripts/07_visualize/00_plot_ia_nb_message_id_overlap.py) plots message-ID overlap and cross-archive reference resolution, reading the `ia_nb_message_id_overlap*.json` files from step 04. Prints reference statistics to stdout and saves .png files to `data/output/07_visualize/plot_ia_nb_message_id_overlap/`.

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
