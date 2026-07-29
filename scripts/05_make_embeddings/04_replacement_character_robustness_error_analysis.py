import argparse
import logging
import shutil
import sys
from pathlib import Path

from usenet_no.replacement_char_robustness import (
    PairSimilarity,
    correlate_with_similarity,
    format_side_by_side,
    lowest_scoring_pairs,
    read_pairs,
    read_similarities,
)
from usenet_no.replacement_chars import ReplacementCharPair

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 100


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Look at where an embedding model lost the most to the"
        " U+FFFD (�) damage: what the similarity it gave a pair follows, and"
        " the pairs it did worst on, the intact NB body and the damaged IA body"
        " side by side, so the low scores can be read against the text that"
        " produced them."
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=20,
        metavar="N",
        help="Print at most N pairs (default: %(default)s)",
    )
    parser.add_argument(
        "--max-score",
        type=float,
        default=0.7,
        help="Only print pairs scoring below this cosine similarity"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--similarities-file",
        type=Path,
        default=Path(
            "data/output/05_make_embeddings/replacement_char_robustness"
            "/jinaai/jina-embeddings-v5-text-nano/similarities.csv"
        ),
        help="Per-pair similarities CSV from"
        " 03_replacement_character_robustness_make_embeddings.py"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--pairs-file",
        type=Path,
        default=Path(
            "data/output/05_make_embeddings/replacement_char_eval_pairs.jsonl"
        ),
        help="The evaluation set the similarities were measured on"
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

    for input_file in (args.similarities_file, args.pairs_file):
        if not input_file.exists():
            logger.error("%s does not exist", input_file)
            sys.exit(1)

    width = args.width or shutil.get_terminal_size((DEFAULT_WIDTH, 24)).columns
    similarities = read_similarities(args.similarities_file)
    pairs = read_pairs(args.pairs_file)

    if not similarities:
        logger.error("%s holds no scored pairs", args.similarities_file)
        sys.exit(1)

    print(format_correlations(similarities, width))

    examples = lowest_scoring_pairs(
        similarities, pairs, args.num_examples, args.max_score
    )
    if not examples:
        logger.info(
            "No pairs scored below %s in %s", args.max_score, args.similarities_file
        )
        sys.exit(0)

    for rank, (similarity, pair) in enumerate(examples, start=1):
        print(format_example(rank, similarity, pair, width))

    logger.info(
        "Printed %d of the %d pairs scoring below %s",
        len(examples),
        sum(
            similarity.matched_similarity < args.max_score
            for similarity in similarities
        ),
        args.max_score,
    )
