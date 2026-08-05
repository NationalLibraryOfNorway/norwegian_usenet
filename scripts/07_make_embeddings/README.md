# Step 07: embed messages

These scripts read the mbox files rather than the database, since embedding needs the message text itself, which the database stores only as a hash.

- [00_select_newsgroups.py](00_select_newsgroups.py) writes the top 50 newsgroups by combined unique message count, reading `data/output/04_compare_archives/ia_nb_content_comparison_date_filtered.csv` (from step 04) and keeping only groups where both archives contribute unique messages. Creates `data/output/07_make_embeddings/newsgroups_for_selection.jsonl`, meant as candidates when choosing the `--selection` newsgroups for the scripts below.
- [02_embed_messages.py](02_embed_messages.py) makes text embeddings for each message in a selection of newsgroups from both archives, with a sentence-transformers model. The IA archive runs past the NB one at both ends, so only IA messages inside the NB date span are embedded; the database says which those are, and they are read from `data/input/internet_archive/utf_8_data` at the positions it gives. Writes the embeddings, and the positions they came from, to `data/output/07_make_embeddings/<model>/`.
- [03_umap_reduce_embeddings.py](03_umap_reduce_embeddings.py) reduces the embeddings to 2 dimensions with UMAP, and caches the result in `data/output/07_make_embeddings/umap_embeddings/<model>/`.
