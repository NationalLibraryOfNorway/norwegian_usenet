# Step 01: extracting and parsing the data

The scripts for preparing the data for analysis live in this directory.

- [01_extract_nb_archive_and_find_stubbed_newsgroup_names.py](01_extract_nb_archive_and_find_stubbed_newsgroup_names.py) extracts the NB tar archives to `data/input/nb/unzipped_data`, then finds newsgroup names the KZ2001-0147 CD cut off to 8 characters (8.3 file naming), by matching them against the other NB sources' names at the same position in the newsgroup tree. Writes the pairs to `data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv`, which is meant to be reviewed before running the next script and can carry hand-added rows.
- [02_parse_nb_archive.py](02_parse_nb_archive.py) reads the extracted NB data and writes one utf-8-encoded .mbox file per newsgroup. Newsgroup names listed in `data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv` are replaced when building the mbox filenames, so messages from a cut-off directory land in the same file as the sources that carry the full name.
- [03_scrape_internet_archive.py](03_scrape_internet_archive.py) fetches and downloads all zip files from `https://archive.org/download/usenet-no` (stored in `data/input/internet_archive/zipped_data` by default).
- [04_parse_internet_archive.py](04_parse_internet_archive.py) unzips and reads all mbox files from the scrape output. Files are decoded and re-encoded to UTF-8 and written to `data/input/internet_archive/utf_8_data`.
- [05_sanity_check_nb_message_count.py](05_sanity_check_nb_message_count.py) checks that each NB mbox file holds as many messages as the number of source files it was written from. Exits non-zero when they disagree. The IA sources are mbox files themselves, so they have no equivalent count to check against.

## Cut-off newsgroup names

The pairs currently in [cut_off_newsgroup_names.csv](../../data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv):

| cut_off_name | full_name |
| --- | --- |
| no.alt.diskusjo | no.alt.diskusjoner |
| no.alt.frustras | no.alt.frustrasjoner |
| no.alt.gledesut | no.alt.gledesutbrudd |
| no.alt.motorsyk | no.alt.motorsykler |
| no.alt.tegneser | no.alt.tegneserier |
| no.biz.diskusjo | no.biz.diskusjoner |
| no.elektron | no.elektronikk |
| no.havforsk | no.havforskning |
| no.kryptogr | no.kryptografi |
| no.litterat | no.litteratur |
| no.multimed | no.multimedia |
| no.org.efn.diskusjo | no.org.efn.diskusjon |
| no.psykolog | no.psykologi |
| no.storting | no.stortinget |
| no.tungregn | no.tungregning |
| no.typograf | no.typografi |

## Encodings

Neither archive declares its encoding, so both parse scripts detect it with chardet (`usenet_no.archives.encoding`) and fall back to latin-1 when nothing is detected, or when the detected encoding is one chardet is known to misreport on the short NB message files (VISCII, EUC-TW). Both detect one encoding per file in `unzipped_data`; the IA files are one mbox per newsgroup, the NB files one message each. Both scripts write what they detected to `encodings.json` next to the archive's data directories, keyed by the source file's path under `unzipped_data`.