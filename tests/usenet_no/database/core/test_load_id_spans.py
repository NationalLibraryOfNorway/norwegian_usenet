import pytest

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.core import load_id_spans


def test_spans_follow_load_order(mbox_data, load_archives):
    connection = load_archives(
        [
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    assert load_id_spans(connection) == {
        (IA_ARCHIVE, "no.replacement.chars"): (1, 5),
        (NB_ARCHIVE, "no.replacement.chars"): (1, 4),
    }


def test_raises_on_gap_in_row_ids(mbox_data, load_archives):
    connection = load_archives(
        [(mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE)]
    )
    connection.execute(f"DELETE FROM {IA_ARCHIVE}.messages WHERE id = 3")

    with pytest.raises(ValueError, match="not contiguous"):
        load_id_spans(connection)
