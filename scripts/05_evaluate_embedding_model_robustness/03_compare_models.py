import argparse
import logging
import shutil
import sys
from pathlib import Path

from usenet_no.replacement_chars import ReplacementCharPair
from usenet_no.replacement_chars.robustness import (
    ModelRun,
    PairSimilarity,
    RobustnessSummary,
    correlate_with_similarity,
    format_side_by_side,
    lowest_scoring_pairs,
    rank_by_weighted_score,
    read_model_runs,
    read_pairs,
    weighted_score,
)

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 100


def format_model_heading(
    summary: RobustnessSummary,
    matched_weight: float,
    shuffled_weight: float,
    width: int,
) -> str:
    """What one model scored on the whole evaluation set."""
    score = weighted_score(summary, matched_weight, shuffled_weight)
    return "\n".join(
        [
            "#" * width,
            f"{summary.model} — {summary.num_pairs} pairs",
            "#" * width,
            f"  weighted score  {score:+.4f}"
            f"  = {matched_weight:g} × matched mean {summary.matched.mean:.4f}"
            f" − {shuffled_weight:g} × shuffled mean {summary.shuffled.mean:.4f}",
            f"  matched   mean {summary.matched.mean:.4f}"
            f"  p05 {summary.matched.percentiles['p05']:.4f}"
            f"  min {summary.matched.min:.4f}",
            f"  shuffled  mean {summary.shuffled.mean:.4f}",
            f"  p95 {summary.shuffled.percentiles['p95']:.4f}",
            f"  max {summary.shuffled.max:.4f}",
            "",
        ]
    )


def format_correlations(similarities: list[PairSimilarity], width: int) -> str:
    """The Pearson r of each measure of a pair against the similarity it scored."""
    correlations = correlate_with_similarity(similarities)
    label_width = max(len(label) for label in correlations)
    return "\n".join(
        [
            "=" * width,
            f"Pearson r with similarity, over {len(similarities)} pairs",
            "=" * width,
            *(
                f"  {label:<{label_width}}  {value:+.3f}"
                for label, value in correlations.items()
            ),
            "",
        ]
    )


def format_example(
    rank: int,
    similarity: PairSimilarity,
    pair: ReplacementCharPair,
    width: int,
) -> str:
    """One example: what it scored, then the two bodies next to each other."""
    heading = (
        f"{rank}. {similarity.newsgroup} {similarity.message_id_hash}"
        f" — similarity {similarity.matched_similarity:.4f}"
        f" (baseline {similarity.shuffled_similarity:.4f},"
        f" {similarity.replacement_char_count} replacement chars"
        f" in {similarity.nb_body_length} characters)"
    )
    return "\n".join(
        [
            "=" * width,
            heading,
            "=" * width,
            format_side_by_side(
                "NB (intact)", pair.nb_body, "IA (�)", pair.ia_body, width
            ),
            "",
        ]
    )


def format_ranking(
    runs: list[ModelRun],
    matched_weight: float,
    shuffled_weight: float,
    width: int,
) -> str:
    """Every model's weighted score, best first, and the model holding the best."""
    ranking = rank_by_weighted_score(runs, matched_weight, shuffled_weight)
    model_width = max(len(run.summary.model) for run, _ in ranking)
    best_run, best_score = ranking[0]
    return "\n".join(
        [
            "#" * width,
            f"Weighted score, {matched_weight:g} × matched mean"
            f" − {shuffled_weight:g} × shuffled mean",
            "#" * width,
            *(
                f"  {rank}. {run.summary.model:<{model_width}}  {score:+.4f}"
                f"  (matched {run.summary.matched.mean:.4f},"
                f" shuffled {run.summary.shuffled.mean:.4f},"
                f" {run.summary.num_pairs} pairs)"
                for rank, (run, score) in enumerate(ranking, start=1)
            ),
            "",
            f"Best weighted score: {best_run.summary.model} ({best_score:+.4f})",
            "",
        ]
    )


def print_model_run(
    run: ModelRun,
    pairs: list[ReplacementCharPair],
    args: argparse.Namespace,
    width: int,
) -> None:
    """One model: what it scored, what its scores follow, and its worst pairs."""
    print(
        format_model_heading(
            run.summary, args.matched_weight, args.shuffled_weight, width
        )
    )
    print(format_correlations(run.similarities, width))

    examples = lowest_scoring_pairs(
        run.similarities, pairs, args.num_examples, args.max_score
    )
    if not examples:
        logger.info(
            "No pairs scored below %s for %s", args.max_score, run.summary.model
        )
        return

    for rank, (similarity, pair) in enumerate(examples, start=1):
        print(format_example(rank, similarity, pair, width))

    logger.info(
        "%s: printed %d of the %d pairs scoring below %s",
        run.summary.model,
        len(examples),
        sum(
            similarity.matched_similarity < args.max_score
            for similarity in run.similarities
        ),
        args.max_score,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Look at where the embedding models lost the most to the"
        " U+FFFD (�) damage: for every model run in the results directory, what"
        " the similarity it gave a pair follows, and the pairs it did worst on,"
        " the intact NB body and the damaged IA body side by side, so the low"
        " scores can be read against the text that produced them. Ends with the"
        " models ranked by a weighted score of their matched and shuffled"
        " similarities."
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=5,
        metavar="N",
        help="Print at most N pairs per model, 0 prints none (default: %(default)s)",
    )
    parser.add_argument(
        "--max-score",
        type=float,
        default=0.7,
        help="Only print pairs scoring below this cosine similarity"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--results-directory",
        type=Path,
        default=Path("data/output/05_evaluate_embedding_model_robustness"),
        help="Directory of per-model results from 02_make_embeddings.py, each"
        " holding a summary.json and a similarities.csv (default: %(default)s)",
    )
    parser.add_argument(
        "--pairs-file",
        type=Path,
        default=Path(
            "data/output/05_evaluate_embedding_model_robustness/replacement_char_eval_pairs.jsonl"
        ),
        help="The evaluation set the similarities were measured on"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--matched-weight",
        type=float,
        default=1.0,
        metavar="W",
        help="Weight on the mean matched similarity in the score"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--shuffled-weight",
        type=float,
        default=1.0,
        metavar="W",
        help="Weight on the mean shuffled similarity, which the score subtracts"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=0,
        metavar="N",
        help="Characters per line, both columns together (default: the terminal"
        f" width, or {DEFAULT_WIDTH} when it is not known)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    for input_path in (args.results_directory, args.pairs_file):
        if not input_path.exists():
            logger.error("%s does not exist", input_path)
            sys.exit(1)

    width = args.width or shutil.get_terminal_size((DEFAULT_WIDTH, 24)).columns
    runs = read_model_runs(args.results_directory)
    pairs = read_pairs(args.pairs_file)

    if not runs:
        logger.error("%s holds no model runs", args.results_directory)
        sys.exit(1)

    for run in runs:
        if not run.similarities:
            logger.warning(
                "%s holds no scored pairs, leaving it out", run.summary.model
            )
    runs = [run for run in runs if run.similarities]
    if not runs:
        logger.error("No model run in %s holds scored pairs", args.results_directory)
        sys.exit(1)

    for run in runs:
        print_model_run(run, pairs, args, width)

    print(format_ranking(runs, args.matched_weight, args.shuffled_weight, width))
