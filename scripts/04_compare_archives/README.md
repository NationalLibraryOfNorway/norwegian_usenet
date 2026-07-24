# Step 04: comparing archives

These scripts all read `data/output/02_build_database/usenet.db`. The scripts are unnumbered (all with a `00_` prefix) because they are independent of each other and can be run in any order.

- [00_compare_ia_nb_message_content.py](00_compare_ia_nb_message_content.py) compares message body overlap between IA and NB by exact text match, per newsgroup. Creates `data/output/04_compare_archives/ia_nb_content_comparison.csv` and `data/output/04_compare_archives/ia_nb_content_comparison_date_filtered.csv`
- [00_compare_ia_nb_message_ids.py](00_compare_ia_nb_message_ids.py) compares message-ID overlap between IA and NB, and collects external references. Creates `data/output/04_compare_archives/ia_nb_message_id_overlap.json`, `data/output/04_compare_archives/ia_nb_message_id_overlap_date_filtered.json`, `data/output/04_compare_archives/ia_nb_message_id_comparison.csv` and `data/output/04_compare_archives/ia_nb_message_id_comparison_date_filtered.csv`
- [00_find_conflicting_message_ids_across_archives.py](00_find_conflicting_message_ids_across_archives.py) finds Message-IDs held by both archives whose copies never agree on a body. Creates `data/output/04_compare_archives/conflicting_message_ids_across_archives.jsonl`.
