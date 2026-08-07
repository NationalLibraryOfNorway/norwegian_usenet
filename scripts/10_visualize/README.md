# Step 10: visualize

These scripts need the plotting libraries in the optional `viz` dependency group, which is not installed by default. Install it with `uv sync --group viz`.

To run graph plotting scripts with the default selection from the embedding scripts, append this to run command:
```
--selection no.religion no.bil no.musikk no.slekt no.litteratur no.prat.politikk
```

- [plot_replacement_char_body_conflicts.py](plot_replacement_char_body_conflicts.py) plots the IA/NB body conflicts summed across newsgroups as bars scaled to their share of all conflicts: all conflicts, the ones whose IA body contains the U+FFFD replacement character, and the ones that are equal after char replacement, reading `replacement_char_body_conflicts.csv` from step 04. Prints the summed counts to stdout and saves `replacement_char_body_conflicts_bars.png` to `data/output/10_visualize/plot_replacement_char_body_conflicts/`.
- [plot_newsgroup_overlap_graph.py](plot_newsgroup_overlap_graph.py) draws a graph of newsgroups, with edges based on user overlap. The script reads a `newsgroup_user_jaccard_overlap_*.csv` file from step 09. A pair becomes an edge if it clears both `--jaccard-threshold` and `--min-shared-users`, and the layout places newsgroups at a distance of 1 - jaccard from each other. Every newsgroup in the input file is drawn, unless `--selection` names the ones to draw. Saves an interactive .html figure, named after the input file, the two thresholds and any selection, to `data/output/10_visualize/plot_newsgroup_overlap_graph/`. (The current script is adapted for the current default input file, the graph layout may look bad if input file is changed)
- [plot_newsgroup_reference_graph.py](plot_newsgroup_reference_graph.py) draws a directed graph of newsgroups, with arrows for the references between them, reading a reference edge list CSV from step 09 and the `messages_per_group_*.csv` files from step 03, which size the vertices by message count. An edge is drawn if it carries at least `--min-references` references, and its width follows the count. The `unknown` placeholder is drawn as a diamond unless `--exclude-unknown` is flagged, and `--selection` names the newsgroups to draw. Saves an interactive .html figure, named after the input file, any selection, the unknown flag and the threshold, to `data/output/10_visualize/plot_newsgroup_reference_graph/`.
