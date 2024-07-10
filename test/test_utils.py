import pprint
from pathlib import Path
from typing import Any

from csv_diff import compare, load_csv


def assert_csv_files_are_identical(
    correct_output_file: Path, test_output_file: Path
) -> None:
    with open(correct_output_file, encoding="utf8") as a, open(
        test_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list[Any]] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)

        # the diff dict should contain five empty lists:
        # - 'added'
        # - 'changed'
        # - 'columns_added'
        # - 'columns_removed'
        # - 'removed'
        assert len(diff) != 0  # sanity check

        for _list in diff.values():
            assert len(_list) == 0
