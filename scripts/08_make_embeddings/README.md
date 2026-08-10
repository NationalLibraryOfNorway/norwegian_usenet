# Step 08: embed messages

These scripts read the mbox files rather than the database, since embedding needs the message text itself, which the database stores only as a hash.

[03_visualize_embeddings.py](03_visualize_embeddings.py) needs the plotting libraries in the optional `viz` dependency group, which is not installed by default. Install it with `uv sync --group viz`.

- [00_select_newsgroups.py](00_select_newsgroups.py) writes the top 50 newsgroups by combined unique message count, reading `data/output/04_compare_message_bodies/ia_nb_content_comparison.csv` (from step 04) and keeping only groups where both archives contribute unique messages. Creates `data/output/08_make_embeddings/newsgroups_for_selection.jsonl`, meant as candidates when choosing the `--selection` newsgroups for the scripts below.
- [01_embed_messages.py](01_embed_messages.py) makes text embeddings for each message in a selection of newsgroups from both archives, with a sentence-transformers model. The IA archive runs past the NB one at both ends, so only IA messages inside the NB date span are embedded; the database says which those are, and they are read from `data/input/internet_archive/utf_8_data` at the positions it gives. Writes the embeddings, and the positions they came from, to `data/output/08_make_embeddings/<model>/`.
- [02_umap_reduce_embeddings.py](02_umap_reduce_embeddings.py) reduces the embeddings to 2 dimensions with UMAP, and caches the result in `data/output/08_make_embeddings/umap_embeddings/<model>/`.
- [03_visualize_embeddings.py](03_visualize_embeddings.py) plots those 2-dimensional embeddings as an interactive Plotly scatter plot, coloured by newsgroup and shaped by archive. The legend holds one entry per newsgroup and archive, or one per newsgroup covering both archives when `--flatten-legend` is flagged. Opens in a browser.
