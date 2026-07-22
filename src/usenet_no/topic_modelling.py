def make_run_tag(
    nr_topics: int | None,
    selection: list[str],
) -> str:
    parts = ["_".join(sorted(selection))]
    if nr_topics is not None:
        parts.append(f"nr{nr_topics}")
    return "_".join(parts) if parts else "default"
