# Step 01.06: the message header fields

These scripts read the archive sources that steps 01 to 04 extracted, and report on the headers their messages carry. They change nothing in the archive data, and each writes to `data/output/01_extract_and_parse_usenet_data/`.

The sections below record what the checks on the IA parse found. The scripts that ran those checks have been removed; the parse behaviour they confirmed is covered by the unit tests of `usenet_no.mbox_utils` and `usenet_no.archives.parse_internet_archive`.

- [01_count_nb_header_fields.py](01_count_nb_header_fields.py) reads the header block of every NB source file listed in `data/input/nb/encodings.json`, decoding it with the encoding detected there, and writes one row per message header field with the number of messages carrying it to `nb_header_field_counts.csv`.
- [02_count_ia_header_fields.py](02_count_ia_header_fields.py) counts the same fields in the IA sources, which are one mbox file per newsgroup rather than one file per message: every mbox file listed in `data/input/internet_archive/encodings.json` is split into messages, and each message's header block is decoded with the encoding detected for the file it is in. Writes `ia_header_field_counts.csv`.

The two counting scripts match field names case-insensitively and report each field under the spelling most of its messages use; a field repeated within one message counts once. The core fields, the ones the analysis reads a message by, are `Date`, `From`, `Message-ID`, `Newsgroups` and `Subject`; every IA source message carries all five. They are matched case-insensitively too, so a message spelling it `Message-Id` carries it.

## Lone carriage returns

A carriage return that no newline follows is not a line ending to a reader that splits on newlines, but is one to `email`'s parser, which ends the header line there. The line it leaves behind is no header and no folded value, so the parser reads the rest of the message as body and every field below the break is lost.

The IA sources hold 32 messages with one in the header block and 691 with one in the body; the NB sources hold none. In the header block it stands for one of two things, and `04_parse_internet_archive.py` writes `utf_8_data` accordingly: a carriage return with a header line right after it ended that line, and becomes a newline; one inside a header value is taken out, so the value stays a single line. The body is left as it stands.

`field_names` splits header blocks on carriage returns too, and passes over a line that is no field rather than stopping at it, so the counts above are the same for a source message and for its parsed copy. The source files holding a carriage return are listed in `lone_carriage_returns.csv`.

## Header lines the source mangled

`email`'s parser ends a message's headers at the first line that is neither a field nor a folded value, and reads the rest as body, so every field below such a line is lost. `database/build.py` reads through that parser. Three shapes of line do it in the IA sources: a field name carrying a byte outside printable ASCII (`X-gåte:`), a `Received` value Google Groups folded at column 0, and one message with a run of control bytes in front of an otherwise good header.

`04_parse_internet_archive.py` repairs each of them: junk in front of a field name is taken off, and a line that is no field either way is indented, folding it into the header line above. The mangled line's own field is the only one that can be lost, and the fields below it are kept.

## Where the messages are split

`mailbox` begins a message at every line starting with `From `, and the IA sources do not escape the ones their message bodies hold, so `StrictMbox` accepts only a line carrying a Google Groups id. A body line taken for an envelope line splits one message in two; an envelope line taken for body text glues two messages into one.

Neither shows up as a missing header field, so each was checked on its own. Every archived article carries an `X-Google-Language` header, and `ia_header_field_counts.csv` reports it on every one of the 5 981 974 messages the split found, so no message was split in two. For the other direction, each of the 3497 `From ` lines the split passed over was checked for a header block following it, and none has one.
