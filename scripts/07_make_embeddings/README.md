# Step 07: embed messages

These scripts read the mbox files rather than the database, since embedding needs the message text itself, which the database stores only as a hash.

- [00_select_newsgroups.py](00_select_newsgroups.py) writes the top 50 newsgroups by combined unique message count, reading `data/output/04_compare_archives/ia_nb_content_comparison_date_filtered.csv` (from step 04) and keeping only groups where both archives contribute unique messages. Creates `data/output/07_make_embeddings/newsgroups_for_selection.jsonl`, meant as candidates when choosing the `--selection` newsgroups for the scripts below.
- [01_filter_internet_archive_by_date.py](01_filter_internet_archive_by_date.py) filters the IA mbox files to only include messages within the date span of the NB archive (reading `data/output/03_statistics_per_archive/date_count_nb.csv`), and writes them to `data/input/internet_archive/date_filtered`. Messages whose date could not be parsed are excluded.
- [02_embed_messages.py](02_embed_messages.py) makes text embeddings for each message in a selection of newsgroups from both archives, with a sentence-transformers model. Writes to `data/output/07_make_embeddings/<model>/`.
- [03_umap_reduce_embeddings.py](03_umap_reduce_embeddings.py) reduces the embeddings to 2 dimensions with UMAP, and caches the result in `data/output/07_make_embeddings/umap_embeddings/<model>/`.
