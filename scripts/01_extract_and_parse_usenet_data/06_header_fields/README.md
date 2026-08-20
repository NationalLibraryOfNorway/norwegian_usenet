# Step 01.06: the message header fields

These scripts read the archive sources that steps 01 to 04 extracted, and report on the headers their messages carry. They change nothing in the archive data, and each writes to `data/output/01_extract_and_parse_usenet_data/`.

- [01_count_nb_header_fields.py](01_count_nb_header_fields.py) reads the header block of every NB source file listed in `data/input/nb/encodings.json`, decoding it with the encoding detected there, and writes one row per message header field with the number of messages carrying it to `nb_header_field_counts.csv`.
- [02_count_ia_header_fields.py](02_count_ia_header_fields.py) counts the same fields in the IA sources, which are one mbox file per newsgroup rather than one file per message: every mbox file listed in `data/input/internet_archive/encodings.json` is split into messages, and each message's header block is decoded with the encoding detected for the file it is in. Writes `ia_header_field_counts.csv`.

The two counting scripts match field names case-insensitively and report each field under the spelling most of its messages use; a field repeated within one message counts once. The core fields, the ones the analysis reads a message by, are `Date`, `From`, `Message-ID`, `Newsgroups` and `Subject`; every IA source message carries all five. They are matched case-insensitively too, so a message spelling it `Message-Id` carries it.
