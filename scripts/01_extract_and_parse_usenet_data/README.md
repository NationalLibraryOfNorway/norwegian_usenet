# Step 01: extracting and parsing the data

The scripts for preparing the data for analysis live in this directory.

- [01_extract_nb_archive_and_find_stubbed_newsgroup_names.py](01_extract_nb_archive_and_find_stubbed_newsgroup_names.py) extracts the NB tar archives to `data/input/nb/unzipped_data`, then finds newsgroup names the KZ2001-0147 CD cut off to 8 characters (8.3 file naming), by matching them against the other NB sources' names at the same position in the newsgroup tree. Writes the pairs to `data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv`, which is meant to be reviewed before running the next script and can carry hand-added rows. Run with `--overwrite` to regenerate that file, discarding any hand-added rows; without the flag the script exits without doing anything when the file is already there.
- [02_parse_nb_archive.py](02_parse_nb_archive.py) reads the extracted NB data and writes one utf-8-encoded .mbox file per newsgroup. Newsgroup names listed in `data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv` are replaced when building the mbox filenames, so messages from a cut-off directory land in the same file as the sources that carry the full name. A newsgroup is spread across the tar archives, so a run writes the whole output directory or none of it. Run with `--overwrite` to clear the output directory and regenerate every mbox file; without the flag the script exits with an error when the directory already holds files.
- [03_scrape_internet_archive.py](03_scrape_internet_archive.py) fetches and downloads all zip files from `https://archive.org/download/usenet-no` (stored in `data/input/internet_archive/zipped_data` by default). Run with `--overwrite` to fetch the file listing and every zip file again; without the flag a zip file already downloaded is skipped.
- [04_parse_internet_archive.py](04_parse_internet_archive.py) unzips and reads all mbox files from the scrape output. Files are decoded and re-encoded to UTF-8 and written to `data/input/internet_archive/utf_8_data`. Run with `--overwrite` to decode every file again from scratch; without the flag a file already written, whose detected encoding is in `encodings.json`, is skipped.
- [05_sanity_check_nb_message_count.py](05_sanity_check_nb_message_count.py) checks that each NB mbox file holds as many messages as the number of source files it was written from. Exits non-zero when they disagree. The IA sources are mbox files themselves, so they have no equivalent count to check against.
- [06_header_fields/](06_header_fields) counts the header fields the messages of both archives carry, one row per field. Neither script changes the archive data. See [06_header_fields/README.md](06_header_fields/README.md), which also records what the checks on the IA parse found.

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

## Unescaped "From " lines in the IA archive

An mbox file separates its messages with an envelope line beginning with `From `, and escapes a body line that begins the same way by writing `>From `. The IA sources do not: a message body that opens a line with `From ` keeps it as it stands, and `mailbox.mbox` starts a new message at every one of them.

Every IA envelope line carries the Google Groups id the archive was scraped with, a `From ` and a signed integer, so `usenet_no.mbox_utils.StrictMbox` accepts only a line of that form and reads the rest as body text. That leaves 3497 `From ` lines across the archive, each of which was checked: none is followed by a header block, so none of them begins a message.

[04_parse_internet_archive.py](04_parse_internet_archive.py) escapes them on the way out, so every `From ` line in `data/input/internet_archive/utf_8_data` is an envelope line and the file reads as a plain mbox. The NB sources hold one message per file, so they raise no such question.

## Encodings

Neither archive declares its encoding, so both parse scripts detect it with chardet (`usenet_no.archives.encoding`) and fall back to latin-1 when nothing is detected, or when the detected encoding is one chardet is known to misreport on the short NB message files (VISCII, EUC-TW). Both detect one encoding per file in `unzipped_data`; the IA files are one mbox per newsgroup, the NB files one message each. Both scripts write what they detected to `encodings.json` next to the archive's data directories, keyed by the source file's path under `unzipped_data`.