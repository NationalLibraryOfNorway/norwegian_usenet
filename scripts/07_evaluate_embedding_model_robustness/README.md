# Step 07: evaluate embedding model robustness

These scripts measure how robust an embedding model is to the U+FFFD (`�`) damage in the IA archive. They come before step 08 because their answer decides which model the embeddings there are made with.

They read the mbox files as well as the database, since embedding needs the message text itself, which the database stores only as a hash.

- [01_make_dataset.py](01_make_dataset.py) builds the evaluation set for the robustness check: the message bodies behind the `messages_equal_with_char_replacement` count in step 04, as pairs of the damaged IA body and the intact NB body of the same message. Both bodies are whitespace-normalized (every run of whitespace collapsed to a single space, ends stripped), so that the two texts of a pair differ in nothing but the replacement characters — the archives wrap and space the same posting differently, and that difference would otherwise be measured along with the U+FFFD damage. Reads `data/output/02_build_database/usenet.db` for the conflicts and the mbox files in `data/input/` for the body texts. The pairs are deduplicated on the hashed message id, keeping the copy from the newsgroup that contributes the fewest pairs. Writes at most `--max-pairs` of them (default 5000, `0` writes all), spread as evenly over the newsgroups as their sizes allow, to `data/output/07_evaluate_embedding_model_robustness/replacement_char_eval_pairs.jsonl`. The file holds message text and is not shared. Run with `--overwrite` to rewrite it; without the flag the script exits without doing anything when it is already there.
- [02_evaluate_embedding_model.py](02_evaluate_embedding_model.py) embeds both sides of every pair with `--model` and measures the cosine similarity between them. Each IA body is also scored against another pair's NB body, giving the similarity unrelated messages get from the same model. Writes `summary.json` (the distribution of both sets of similarities) and `similarities.csv` (one row per pair, with the newsgroup, the hashed message id and the two similarities) to `data/output/07_evaluate_embedding_model_robustness/<model>/`. Run with `--overwrite` to rewrite those files; without the flag the script exits without doing anything when that model's `summary.json` is already there. Pass `--task clustering` for the Jina models, and `--prompt-prefix` for models asking for the text in a set form, which puts the string in front of both bodies of every pair before they are encoded (`--prompt-prefix 'task: clustering | query: '` for `nicher92/saga-embed_v1`).
- [03_compare_models.py](03_compare_models.py) reads every model run under `--results-directory` back: each directory holding both a `summary.json` and a `similarities.csv`. For each model it prints the summary means, the weighted score, the Pearson r between the similarity a pair scored and each of three measures of it (how many replacement characters it holds, how long it is, and how dense the damage is), and then the pairs the model scored lowest, the intact NB body and the damaged IA body in two columns. It prints the `--num-examples` (default 5) worst-scoring pairs per model that score below `--max-score` (default 0.7), reading the bodies from the evaluation set the similarities were measured on (`--pairs-file`). It ends with every model ranked by its weighted score, best first, and the model holding the best.

## Replacement character robustness

The IA archive lost the Norwegian characters æ, ø and å to the Unicode replacement character U+FFFD (`�`), which step 04 counts per newsgroup. The NB archive holds the same messages with the characters intact, so for a message held by both archives there are two copies of one text: one damaged, one not.

That is what these scripts measure a model on. Both copies of a pair are embedded, and the cosine similarity between the two embeddings says how far the damage moved the message: a model that reads through the damage puts the two copies in nearly the same place, near a similarity of 1, and one that does not places the damaged copy somewhere else.

A similarity on its own has no scale to be read against, so each damaged body is also scored against the intact body of a *different* pair. Those mismatched scores say what similarity two unrelated messages from this collection get from the same model, which is the floor the matched scores mean something against.

### Weighted score

`03_compare_models.py` ranks the models on one number per model, taken from the two means in its `summary.json`:

```
score = matched-weight × mean matched similarity − shuffled-weight × mean shuffled similarity
```

Both weights are 1.0 unless `--matched-weight` and `--shuffled-weight` are passed, so by default the score is the distance between the two means: how much closer a model puts the two copies of one message than it puts two unrelated messages. Setting `--shuffled-weight 0` ranks on the matched mean alone.

### Pearson r

`03_compare_models.py` reports Pearson r between the similarity a pair scored and three measures of that pair: the number of replacement characters in it, the length of the message, and the density of the damage (replacement characters per character).

Pearson r is a number between -1 and +1 saying how closely two measurements move together along a straight line. At +1 one rises exactly as the other rises, at -1 one falls exactly as the other rises, and at 0 knowing one says nothing about the other. It is a direction and a tightness, not an amount: r says nothing about how much similarity is lost per replacement character, only how consistently the two move together. It also only sees straight-line relationships, so a real but curved relationship shows up as a weak r, and it is reported here as one number over all the pairs, which a small group of outlying pairs can pull on.

## Results
We ran evaluation of the following models:
  - codefuse-ai/F2LLM-v2-0.6B
  - intfloat/multilingual-e5-large-instruct
  - jinaai/jina-embeddings-v5-text-nano
  - NbAiLab/nb-sbert-v2-base
  - nicher92/saga-embed_v1
  - Qwen/Qwen3-Embedding-0.6B

on the same subset of 5000 pairs. 

For `jinaai/jina-embeddings-v5-text-nano`, 02_evaluate_embedding_model.py was run with `--task clustering`  
For `nicher92/saga-embed_v1`,  02_evaluate_embedding_model.py was run with `--prompt-prefix "task: clustering | query: "`

The overall best model was `codefuse-ai/F2LLM-v2-0.6B`:

``` 
################################################################################################################################################################
Weighted score, 1 × matched mean − 1 × shuffled mean
################################################################################################################################################################
  1. codefuse-ai/F2LLM-v2-0.6B                +0.7259  (matched 0.9701, shuffled 0.2441, 5000 pairs)
  2. Qwen/Qwen3-Embedding-0.6B                +0.7078  (matched 0.9791, shuffled 0.2713, 5000 pairs)
  3. NbAiLab/nb-sbert-v2-base                 +0.6665  (matched 0.9846, shuffled 0.3181, 5000 pairs)
  4. jinaai/jina-embeddings-v5-text-nano      +0.4398  (matched 0.9944, shuffled 0.5546, 5000 pairs)
  5. nicher92/saga-embed_v1                   +0.3439  (matched 0.9805, shuffled 0.6366, 5000 pairs)
  6. intfloat/multilingual-e5-large-instruct  +0.1541  (matched 0.9905, shuffled 0.8364, 5000 pairs)

Best weighted score: codefuse-ai/F2LLM-v2-0.6B (+0.7259)
``` 

See the full output of 03_compare_models.py at [data/output/07_evaluate_embedding_model_robustness/model_comparison.txt](../../data/output/07_evaluate_embedding_model_robustness/model_comparison.txt)