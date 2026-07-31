"""Measuring how much U+FFFD damage in the IA bodies moves an embedding model.

The evaluation set is built by `usenet_no.replacement_chars.pairs`: pairs of
bodies that are the same posting in the two archives, where the IA copy lost
æ/ø/å/Æ/Ø/Å to the replacement character U+FFFD and the NB copy did not. The
measurement is the cosine similarity between the embeddings of the two copies.

A second set of similarities scores the same IA embeddings against NB
embeddings of *other* pairs (a derangement, so no pair keeps its own partner),
giving the similarity unrelated messages in this collection get from the model.

A crossposted message conflicts in every newsgroup that carries it, so the same
body pair is collected several times over: `deduplicate_pairs` reduces those to
one, and `sample_pairs` spreads a smaller evaluation set over the newsgroups
instead of letting the largest ones fill it.

Pairs are written to and read from JSONL, since the message bodies cannot go in
the shared database and the three steps (building the set, running a model on
it, reading the pairs it did worst on) are separate scripts.
"""

import csv
import json
import logging
import textwrap
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from itertools import zip_longest
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from usenet_no.replacement_chars.pairs import ReplacementCharPair

logger = logging.getLogger(__name__)

PERCENTILES = (1, 5, 25, 50, 75, 95, 99)

_COLUMN_SEPARATOR = " | "
_MIN_COLUMN_WIDTH = 20


@dataclass
class SimilarityStatistics:
    """The distribution of one set of cosine similarities."""

    mean: float
    std: float
    min: float
    max: float
    percentiles: dict[str, float]


@dataclass
class RobustnessSummary:
    """What a single model scored on the evaluation set."""

    model: str
    num_pairs: int
    matched: SimilarityStatistics
    shuffled: SimilarityStatistics


@dataclass
class PairSimilarity:
    """One row of the per-pair similarities a model run writes out."""

    newsgroup: str
    message_id_hash: str
    replacement_char_count: int
    nb_body_length: int
    matched_similarity: float
    shuffled_similarity: float


@dataclass
class ModelRun:
    """Both output files of one model run, read back."""

    summary: RobustnessSummary
    similarities: list[PairSimilarity]


def write_pairs(pairs: list[ReplacementCharPair], output_file: Path) -> None:
    """Write the pairs as JSONL, one pair per line."""
    with output_file.open(mode="w", encoding="utf-8") as file:
        for pair in pairs:
            file.write(json.dumps(asdict(pair), ensure_ascii=False) + "\n")


def read_pairs(input_file: Path) -> list[ReplacementCharPair]:
    """Read back a JSONL file written by `write_pairs`."""
    with input_file.open(encoding="utf-8") as file:
        return [
            ReplacementCharPair(**json.loads(line)) for line in file if line.strip()
        ]


def read_similarities(input_file: Path) -> list[PairSimilarity]:
    """Read back the per-pair similarities CSV a model run writes out."""
    with input_file.open(newline="", encoding="utf-8") as file:
        return [
            PairSimilarity(
                newsgroup=row["newsgroup"],
                message_id_hash=row["message_id_hash"],
                replacement_char_count=int(row["replacement_char_count"]),
                nb_body_length=int(row["nb_body_length"]),
                matched_similarity=float(row["matched_similarity"]),
                shuffled_similarity=float(row["shuffled_similarity"]),
            )
            for row in csv.DictReader(file)
        ]


def read_summary(input_file: Path) -> RobustnessSummary:
    """Read back the summary JSON a model run writes out."""
    summary = json.loads(input_file.read_text(encoding="utf-8"))
    return RobustnessSummary(
        model=summary["model"],
        num_pairs=summary["num_pairs"],
        matched=SimilarityStatistics(**summary["matched"]),
        shuffled=SimilarityStatistics(**summary["shuffled"]),
    )


def read_model_runs(directory: Path) -> list[ModelRun]:
    """Read every model run under `directory`, in model name order.

    A run is a directory holding both a `summary.json` and a `similarities.csv`;
    one holding only a summary is left out with a warning.
    """
    runs = []
    for summary_file in sorted(directory.glob("**/summary.json")):
        similarities_file = summary_file.with_name("similarities.csv")
        if not similarities_file.exists():
            logger.warning(
                "No %s next to %s, skipping it", similarities_file.name, summary_file
            )
            continue
        runs.append(
            ModelRun(
                summary=read_summary(summary_file),
                similarities=read_similarities(similarities_file),
            )
        )
    return sorted(runs, key=lambda run: run.summary.model)


def weighted_score(
    summary: RobustnessSummary,
    matched_weight: float = 1.0,
    shuffled_weight: float = 1.0,
) -> float:
    """The weighted mean matched similarity less the weighted mean shuffled one."""
    return (
        matched_weight * summary.matched.mean - shuffled_weight * summary.shuffled.mean
    )


def rank_by_weighted_score(
    runs: Iterable[ModelRun],
    matched_weight: float = 1.0,
    shuffled_weight: float = 1.0,
) -> list[tuple[ModelRun, float]]:
    """The runs with their weighted score, best first, ties broken by model name."""
    scored = [
        (run, weighted_score(run.summary, matched_weight, shuffled_weight))
        for run in runs
    ]
    scored.sort(key=lambda scored_run: (-scored_run[1], scored_run[0].summary.model))
    return scored


def lowest_scoring_pairs(
    similarities: list[PairSimilarity],
    pairs: list[ReplacementCharPair],
    num_examples: int,
    max_score: float,
) -> list[tuple[PairSimilarity, ReplacementCharPair]]:
    """The `num_examples` worst-scoring pairs that score below `max_score`.

    Rows whose message id is not in `pairs` are left out with a warning:
    pairing them up anyway would show the bodies of one message next to the
    score of another. Sorted by score, worst first, ties broken by message id.
    """
    pairs_by_message_id = {pair.message_id_hash: pair for pair in pairs}

    examples = []
    for similarity in similarities:
        if similarity.matched_similarity >= max_score:
            continue
        pair = pairs_by_message_id.get(similarity.message_id_hash)
        if pair is None:
            logger.warning(
                "No pair with message id hash %s, skipping it",
                similarity.message_id_hash,
            )
            continue
        examples.append((similarity, pair))

    examples.sort(
        key=lambda example: (example[0].matched_similarity, example[0].message_id_hash)
    )
    return examples[:num_examples]


def correlate_with_similarity(
    similarities: list[PairSimilarity],
) -> dict[str, float]:
    """Correlate each measure of a pair with the similarity the model gave it.

    Pearson r over the scored pairs, for the amount of damage (how many
    replacement characters), the length of the message, and the density of the
    damage (replacement characters per character). A measure that never varies,
    and a set of fewer than two pairs, come back as NaN.
    """
    scores = np.array([row.matched_similarity for row in similarities], dtype=float)
    counts = np.array([row.replacement_char_count for row in similarities], dtype=float)
    lengths = np.array([row.nb_body_length for row in similarities], dtype=float)

    return {
        "replacement char count": _pearson(counts, scores),
        "body length": _pearson(lengths, scores),
        "damage density (chars per character)": _pearson(
            np.divide(
                counts, lengths, out=np.full_like(counts, np.nan), where=lengths > 0
            ),
            scores,
        ),
    }


def _pearson(values: np.ndarray, scores: np.ndarray) -> float:
    """Pearson r, or NaN where it is not defined."""
    if len(values) < 2 or np.any(np.isnan(values)):
        return float("nan")
    if np.std(values) == 0 or np.std(scores) == 0:
        return float("nan")
    return float(np.corrcoef(values, scores)[0, 1])


def format_side_by_side(
    left_heading: str,
    left_text: str,
    right_heading: str,
    right_text: str,
    width: int,
) -> str:
    """Lay two texts out in two columns of a combined `width` characters.

    Both columns wrap at the same width, which puts the same words on the same
    line on either side of a pair.
    """
    column_width = max((width - len(_COLUMN_SEPARATOR)) // 2, _MIN_COLUMN_WIDTH)
    left_lines = _wrap(left_heading, left_text, column_width)
    right_lines = _wrap(right_heading, right_text, column_width)

    return "\n".join(
        f"{left_line:<{column_width}}{_COLUMN_SEPARATOR}{right_line}".rstrip()
        for left_line, right_line in zip_longest(left_lines, right_lines, fillvalue="")
    )


def _wrap(heading: str, text: str, column_width: int) -> list[str]:
    """One column: its heading, a rule under it, and the text wrapped to width."""
    return [
        heading[:column_width],
        "-" * column_width,
        *(textwrap.wrap(text, column_width) or [""]),
    ]


def deduplicate_pairs(
    pairs: Iterable[ReplacementCharPair],
) -> list[ReplacementCharPair]:
    """Keep one pair per message id, the copy from the smallest newsgroup.

    A crossposted message conflicts in every newsgroup that carries it, so the
    same body pair comes back once per newsgroup, and keeping every copy would
    measure that message several times over.

    The copy kept is the one from the newsgroup contributing the fewest pairs,
    which leaves the small newsgroups the messages they do have rather than
    emptying them into the large ones that share the same crossposts. Ties are
    broken by newsgroup name. Sorted by (newsgroup, message id hash).
    """
    pairs = list(pairs)
    pairs_per_newsgroup = Counter(pair.newsgroup for pair in pairs)

    kept: dict[str, ReplacementCharPair] = {}
    for pair in pairs:
        held = kept.get(pair.message_id_hash)
        if held is None or _newsgroup_rank(pair, pairs_per_newsgroup) < _newsgroup_rank(
            held, pairs_per_newsgroup
        ):
            kept[pair.message_id_hash] = pair

    return sorted(
        kept.values(), key=lambda pair: (pair.newsgroup, pair.message_id_hash)
    )


def _newsgroup_rank(
    pair: ReplacementCharPair, pairs_per_newsgroup: Counter
) -> tuple[int, str]:
    """How small the pair's newsgroup is, smallest first, ties broken by name."""
    return (pairs_per_newsgroup[pair.newsgroup], pair.newsgroup)


def sample_pairs(
    pairs: list[ReplacementCharPair], max_pairs: int, seed: int
) -> list[ReplacementCharPair]:
    """Sample at most `max_pairs` pairs, spread as evenly over the newsgroups as possible.

    Taken one newsgroup at a time in rounds rather than at random from the whole
    set, so every newsgroup contributes the same number of pairs give or take
    one, and those with fewer contribute all they have. `seed` decides which
    pairs a newsgroup contributes and which newsgroups get the odd extra one.

    `max_pairs` of 0 or less keeps every pair. The sample stays in the order the
    pairs came in.
    """
    if max_pairs <= 0 or len(pairs) <= max_pairs:
        return pairs

    generator = np.random.default_rng(seed)
    positions_by_newsgroup = defaultdict(list)
    for position, pair in enumerate(pairs):
        positions_by_newsgroup[pair.newsgroup].append(position)

    # Each newsgroup's pairs in random order, and the newsgroups themselves in
    # random order, so that neither the newsgroup names nor the order the pairs
    # arrived in decides what a partly filled round holds
    queues = [
        [int(position) for position in generator.permutation(positions)]
        for _, positions in sorted(positions_by_newsgroup.items())
    ]
    queues = [queues[index] for index in generator.permutation(len(queues))]

    chosen: list[int] = []
    while len(chosen) < max_pairs and queues:
        queues = [queue for queue in queues if queue]
        for queue in queues:
            chosen.append(queue.pop())
            if len(chosen) == max_pairs:
                break

    return [pairs[position] for position in sorted(chosen)]


def _embed_pairs(
    pairs: list[ReplacementCharPair],
    model: SentenceTransformer,
    batch_size: int = 1,
    encode_kwargs: dict | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Embed the NB and the IA side of every pair, in one encode call each."""
    kwargs = {"batch_size": batch_size, "show_progress_bar": True} | (
        encode_kwargs or {}
    )
    logger.info("Embedding %d NB bodies", len(pairs))
    nb_embeddings = model.encode([pair.nb_body for pair in pairs], **kwargs)
    logger.info("Embedding %d IA bodies", len(pairs))
    ia_embeddings = model.encode([pair.ia_body for pair in pairs], **kwargs)
    return np.asarray(nb_embeddings), np.asarray(ia_embeddings)


def cosine_similarities(
    left_embeddings: np.ndarray, right_embeddings: np.ndarray
) -> np.ndarray:
    """Row-wise cosine similarity of two equally shaped embedding matrices."""
    if left_embeddings.shape != right_embeddings.shape:
        raise ValueError(
            f"Embedding shapes differ: {left_embeddings.shape} and"
            f" {right_embeddings.shape}"
        )
    left = left_embeddings.astype(np.float64)
    right = right_embeddings.astype(np.float64)
    norms = np.linalg.norm(left, axis=1) * np.linalg.norm(right, axis=1)
    # A zero vector has no direction, so its similarity is left undefined rather
    # than counted as 0, which would read as "unrelated".
    similarities = np.full(len(norms), np.nan)
    np.divide(np.sum(left * right, axis=1), norms, out=similarities, where=norms > 0)
    return similarities


def derangement(size: int, seed: int) -> np.ndarray:
    """A permutation of 0..size-1 that leaves no index in place.

    Pairs every IA body with an NB body that is not its own.
    """
    if size < 2:
        raise ValueError(f"Cannot derange {size} element(s)")
    generator = np.random.default_rng(seed)
    permutation = generator.permutation(size)
    for index in range(size):
        if permutation[index] == index:
            swap_with = (index + 1) % size
            permutation[[index, swap_with]] = permutation[[swap_with, index]]
    return permutation


def _shuffled_similarities(
    nb_embeddings: np.ndarray, ia_embeddings: np.ndarray, seed: int
) -> np.ndarray:
    """Cosine similarity of each IA body against another pair's NB body."""
    permutation = derangement(len(ia_embeddings), seed)
    return cosine_similarities(nb_embeddings[permutation], ia_embeddings)


def summarize_similarities(similarities: np.ndarray) -> SimilarityStatistics:
    """Describe a set of similarities, ignoring the undefined (NaN) ones."""
    return SimilarityStatistics(
        mean=float(np.nanmean(similarities)),
        std=float(np.nanstd(similarities)),
        min=float(np.nanmin(similarities)),
        max=float(np.nanmax(similarities)),
        percentiles={
            f"p{percentile:02d}": float(np.nanpercentile(similarities, percentile))
            for percentile in PERCENTILES
        },
    )


def evaluate_pairs(
    pairs: list[ReplacementCharPair],
    model: SentenceTransformer,
    model_name: str,
    batch_size: int = 1,
    seed: int = 42,
    encode_kwargs: dict | None = None,
) -> tuple[RobustnessSummary, np.ndarray, np.ndarray]:
    """Score one model on the pairs, returning the summary and both similarity sets."""
    nb_embeddings, ia_embeddings = _embed_pairs(pairs, model, batch_size, encode_kwargs)
    matched = cosine_similarities(nb_embeddings, ia_embeddings)
    shuffled = _shuffled_similarities(nb_embeddings, ia_embeddings, seed)
    summary = RobustnessSummary(
        model=model_name,
        num_pairs=len(pairs),
        matched=summarize_similarities(matched),
        shuffled=summarize_similarities(shuffled),
    )
    return summary, matched, shuffled
