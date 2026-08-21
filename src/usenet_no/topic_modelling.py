"""Build and read turftopic models fitted on pre-computed message embeddings."""

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from turftopic import (
    GMM,
    S3,
    ClusteringTopicModel,
    ContextualModel,
    KeyNMF,
    SensTopic,
    Topeax,
)
from turftopic.base import Encoder

METHODS = ("senstopic", "s3", "gmm", "topeax", "keynmf", "clustering")

# The methods that reduce the embeddings to two t-SNE dimensions and read their
# topics off those, rather than off the embeddings as they are.
REDUCING_METHODS = ("topeax", "clustering")

SOURCES = ("nb", "ia")

OUTLIER_TOPIC = -1


def make_run_dir(
    topics_directory: Path,
    model: str,
    newsgroup: str,
    method: str,
    archive: str,
    nr_topics: int | None,
) -> Path:
    """Point at the directory a run of these settings reads and writes."""
    run_dir = topics_directory / model / newsgroup / method / archive
    if nr_topics is not None:
        run_dir = run_dir / f"nr{nr_topics}"
    return run_dir


def build_topic_model(
    method: str,
    nr_topics: int | None,
    encoder: Encoder | str,
    min_df: int = 10,
    random_state: int | None = None,
) -> ContextualModel:
    """Build an unfitted turftopic model of the given method.

    Naming the encoder rather than passing a loaded one keeps it out of the
    serialized model. It embeds the vocabulary, which every method except gmm
    and clustering needs on top of the document embeddings.
    """
    shared = dict(
        encoder=encoder,
        vectorizer=CountVectorizer(min_df=min_df),
        random_state=random_state,
        trf_kwargs={"trust_remote_code": True},
    )

    if method == "senstopic":
        return SensTopic(n_components=_auto_if_none(nr_topics), **shared)
    if method == "gmm":
        return GMM(n_components=_auto_if_none(nr_topics), **shared)
    if method == "s3":
        return S3(n_components=_required(nr_topics, method), **shared)
    if method == "keynmf":
        return KeyNMF(n_components=_required(nr_topics, method), **shared)
    if method == "topeax":
        if nr_topics is not None:
            raise ValueError(
                "topeax finds the number of topics itself, drop --nr-topics"
            )
        return Topeax(**shared)
    if method == "clustering":
        return ClusteringTopicModel(n_reduce_to=nr_topics, **shared)
    raise ValueError(f"Unknown method {method!r}, pick one of {', '.join(METHODS)}")


def _auto_if_none(nr_topics: int | None) -> int | str:
    return "auto" if nr_topics is None else nr_topics


def _required(nr_topics: int | None, method: str) -> int:
    if nr_topics is None:
        raise ValueError(f"{method} cannot pick the number of topics, set --nr-topics")
    return nr_topics


def assign_topics(
    model: ContextualModel, document_topic_matrix: np.ndarray
) -> np.ndarray:
    """Give every document its highest scoring topic.

    Clustering models number their topics in `classes_` and label outliers -1,
    the other methods number theirs by column.
    """
    classes = getattr(model, "classes_", None)
    if classes is None:
        classes = np.arange(document_topic_matrix.shape[1])
    return np.asarray(classes)[document_topic_matrix.argmax(axis=1)]


def count_documents_per_source(
    topics: np.ndarray,
    sources: Sequence[str],
    topic_words: Mapping[int, list[str]],
) -> list[dict]:
    """Count the documents each source archive contributes to each topic."""
    counts = Counter(zip(topics.tolist(), sources, strict=True))
    rows = []
    for topic_id in sorted({int(topic) for topic in topics.tolist()}):
        per_source = {
            f"{source}_message_count": counts[(topic_id, source)] for source in SOURCES
        }
        rows.append(
            {
                "topic_id": topic_id,
                "words": topic_words.get(topic_id, []),
                **per_source,
                "total_message_count": sum(per_source.values()),
            }
        )
    return rows


def make_topic_words(
    topic_info: pd.DataFrame, n_words: int = 10
) -> dict[int, list[str]]:
    """Map every topic id in a topic table to its highest ranking terms."""
    return {
        int(topic_id): [word.strip() for word in ranking.split(",")[:n_words]]
        for topic_id, ranking in zip(
            topic_info["Topic ID"], topic_info["Highest Ranking"], strict=True
        )
    }


def make_topic_labels(topic_info: pd.DataFrame, n_words: int = 5) -> dict[int, str]:
    """Map every topic id in a topic table to a label of its top terms."""
    labels = {}
    for topic_id, ranking in zip(
        topic_info["Topic ID"], topic_info["Highest Ranking"], strict=True
    ):
        topic_id = int(topic_id)
        if topic_id == OUTLIER_TOPIC:
            labels[topic_id] = f"outliers ({OUTLIER_TOPIC})"
            continue
        words = ", ".join(word.strip() for word in ranking.split(",")[:n_words])
        labels[topic_id] = f"Topic {topic_id}: {words}"
    return labels
