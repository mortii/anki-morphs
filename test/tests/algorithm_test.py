from __future__ import annotations

from ankimorphs.recalc import card_score


def test_target_difference_function() -> None:
    correct_values = [3, 2, 1, 0, 0, 0, 1, 4, 9, 16, 25, 36, 49, 64]
    produced_values = []

    for num_all_morphs in range(1, 15):
        _score = card_score._get_morph_targets_difference(
            num_morphs=num_all_morphs,
            high_target=6,
            low_target=4,
            coefficients_high=(1, 0, 0),
            coefficients_low=(0, 1, 0),
        )
        produced_values.append(_score)

    assert correct_values == produced_values
