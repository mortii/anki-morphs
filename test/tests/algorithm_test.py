from __future__ import annotations

import pytest

from ankimorphs.recalc import card_score


@pytest.mark.parametrize(
    "coefficients_high, coefficients_low, expected_values",
    [
        ((1, 0, 0), (0, 1, 0), [3, 2, 1, 0, 0, 0, 1, 4, 9, 16, 25, 36, 49, 64]),
        ((1.5, 0, 0), (0, 2.5, 0), [8, 5, 3, 0, 0, 0, 2, 6, 14, 24, 38, 54, 74, 96]),
    ],
)
def test_target_difference_function(
    coefficients_high: tuple[float, float, float],
    coefficients_low: tuple[float, float, float],
    expected_values: list[int],
) -> None:
    produced_values = []

    for num_all_morphs in range(1, 15):
        _score = card_score._get_morph_targets_difference(
            num_morphs=num_all_morphs,
            high_target=6,
            low_target=4,
            coefficients_high=coefficients_high,
            coefficients_low=coefficients_low,
        )
        produced_values.append(_score)

    assert expected_values == produced_values
