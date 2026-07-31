import argparse
import csv
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from usenet_no.replacement_chars import ReplacementCharPair
from usenet_no.replacement_chars.robustness import (
    RobustnessSummary,
    evaluate_pairs,
    read_pairs,
)

logger = logging.getLogger(__name__)

# Remove noisy info logs when fetching models from huggingface hub
logging.getLogger("httpx").setLevel(logging.WARNING)


def write_similarities_to_csv(
    pairs: list[ReplacementCharPair],
    matched: np.ndarray,
    shuffled: np.ndarray,
    output_file: Path,
) -> None:
    """Write one row per pair, so the summary can be traced back to the messages.

    The bodies themselves are left out: the message id is hashed and the row
    holds only measurements, so this file can be shared while the pairs file
    cannot.
    """
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "newsgroup",
                "message_id_hash",
                "replacement_char_count",
                "nb_body_length",
                "matched_similarity",
                "shuffled_similarity",
            ]
        )
        writer.writerows(
            (
                pair.newsgroup,
                pair.message_id_hash,
                pair.replacement_char_count,
                len(pair.nb_body),
                matched_similarity,
                shuffled_similarity,
            )
            for pair, matched_similarity, shuffled_similarity in zip(
                pairs, matched, shuffled
            )
        )


def log_summary(summary: RobustnessSummary) -> None:
    logger.info(
        "%s on %d pairs: matched mean %.4f (p05 %.4f, min %.4f),"
        " shuffled mean %.4f (p95 %.4f)",
        summary.model,
        summary.num_pairs,
        summary.matched.mean,
        summary.matched.percentiles["p05"],
        summary.matched.min,
        summary.shuffled.mean,
        summary.shuffled.percentiles["p95"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Measure an embedding model's robustness to the U+FFFD (�)"
        " damage in the IA archive: the cosine similarity between the embeddings"
        " of the damaged IA body and the intact NB body of the same message, for"
        " every pair in the evaluation set built by 01_make_dataset.py. Each IA"
        " body is also scored against another pair's NB body, as a floor to read"
        " the matched similarities against.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codefuse-ai/F2LLM-v2-0.6B",
        help="SentenceTransformer model to evaluate (default: %(default)s)",
    )
    parser.add_argument(
        "--pairs-file",
        type=Path,
        default=Path(
            "data/output/05_evaluate_embedding_model_robustness/replacement_char_eval_pairs.jsonl"
        ),
        help="JSONL file of message body pairs (default: %(default)s)",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/output/05_evaluate_embedding_model_robustness"),
        help="Directory to write the per-model results to (default: %(default)s)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        metavar="N",
        help="Batch size for encoding (default: %(default)s)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Task passed to model.encode, for models that take one"
        " (e.g. 'clustering' for the Jina models)",
    )
    parser.add_argument(
        "--prompt-prefix",
        type=str,
        default="",
        help="String put in front of every message body before it is encoded,"
        " for models asking for the text in a set form (e.g."
        " 'task: clustering | query: ' for nicher92/saga-embed_v1)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Seed for the shuffled baseline pairing (default: %(default)s)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing result files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    model_output_dir = args.output_directory / args.model
    summary_file = model_output_dir / "summary.json"
    similarities_file = model_output_dir / "similarities.csv"

    if summary_file.exists() and not args.overwrite:
        logger.info(
            "Output file already exists: %s. Use --overwrite to regenerate.",
            summary_file,
        )
        sys.exit(0)

    if not args.pairs_file.exists():
        logger.error(
            "%s does not exist. Run 01_make_dataset.py first.",
            args.pairs_file,
        )
        sys.exit(1)

    pairs = read_pairs(args.pairs_file)
    logger.info("Read %d pairs from %s", len(pairs), args.pairs_file)

    if len(pairs) < 2:
        # The baseline pairs every IA body with another pair's NB body, which
        # takes at least two pairs
        logger.error("%s holds too few pairs to evaluate", args.pairs_file)
        sys.exit(1)

    logger.info("Loading model %s", args.model)
    model = SentenceTransformer(args.model, trust_remote_code=True)

    summary, matched, shuffled = evaluate_pairs(
        pairs,
        model,
        model_name=args.model,
        batch_size=args.batch_size,
        seed=args.random_seed,
        encode_kwargs={"task": args.task} if args.task else None,
        prompt_prefix=args.prompt_prefix,
    )

    model_output_dir.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    write_similarities_to_csv(pairs, matched, shuffled, similarities_file)

    log_summary(summary)
    logger.info("Wrote %s and %s", summary_file, similarities_file)
