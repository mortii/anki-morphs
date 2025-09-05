import math

from .. import ankimorphs_globals as am_globals
from ..ankimorphs_config import AnkiMorphsConfig
from .card_morphs_metrics import CardMorphsMetrics

# Anki stores the 'due' value of cards as a 32-bit integer
# on the backend, with '2147483647' being the max value before
# overflow. To prevent overflow when cards are repositioned,
# we decrement the second digit (from the left) of the max value,
# which should give plenty of leeway (10^8).
_MAX_SCORE: int = 2_047_483_647

MORPH_UNKNOWN_PENALTY: int = 1_000_000


####################################################################################
#                                      ALGORITHM
####################################################################################
# an in-depth explanation of the algorithm can be found here:
# - docs/src/user_guide/usage/recalc.md
# which can also be viewed here:
# - https://mortii.github.io/anki-morphs/user_guide/usage/recalc.html#scoring-algorithm
#######################################


class CardScore:
    __slots__ = (
        "score",
        "score_terms",
        "due",
    )

    def __init__(
        self, am_config: AnkiMorphsConfig, card_morph_metrics: CardMorphsMetrics
    ) -> None:
        # 'due' will be the same as 'score' except for some edge cases
        self.due = self.score = _MAX_SCORE
        self.score_terms = "N/A"

        if len(card_morph_metrics.all_morphs) == 0:
            # we don't want buggy cards that have no morphs
            # to clog up the start of the card queue, so we
            # give them the max due (default), but we also
            # signal with the score that there are no morphs
            self.score = 0
            return

        all_morphs_target_difference: int = _get_all_morphs_target_difference(
            am_config=am_config,
            num_morphs=len(card_morph_metrics.all_morphs),
        )

        learning_morphs_target_difference: int = _get_learning_morphs_target_difference(
            am_config=am_config,
            num_morphs=card_morph_metrics.num_learning_morphs,
        )

        all_morphs_total_priority_score = (
            am_config.algorithm_total_priority_all_morphs_weight
            * card_morph_metrics.total_priority_all_morphs
        )

        unknown_morphs_total_priority_score = (
            am_config.algorithm_total_priority_unknown_morphs_weight
            * card_morph_metrics.total_priority_unknown_morphs
        )

        learning_morphs_total_priority_score = (
            am_config.algorithm_total_priority_learning_morphs_weight
            * card_morph_metrics.total_priority_learning_morphs
        )

        all_morphs_avg_priority_score = (
            am_config.algorithm_average_priority_all_morphs_weight
            * card_morph_metrics.avg_priority_all_morphs
        )

        learning_morphs_avg_priority_score = (
            am_config.algorithm_average_priority_learning_morphs_weight
            * card_morph_metrics.avg_priority_learning_morphs
        )

        leaning_morphs_target_difference_score = (
            am_config.algorithm_learning_morphs_target_difference_weight
            * learning_morphs_target_difference
        )

        all_morphs_target_difference_score = (
            am_config.algorithm_all_morphs_target_difference_weight
            * all_morphs_target_difference
        )

        tuning: int = (
            all_morphs_total_priority_score
            + unknown_morphs_total_priority_score
            + learning_morphs_total_priority_score
            + all_morphs_avg_priority_score
            + learning_morphs_avg_priority_score
            + leaning_morphs_target_difference_score
            + all_morphs_target_difference_score
        )

        unknown_morphs_amount_score = (
            len(card_morph_metrics.unknown_morphs) * MORPH_UNKNOWN_PENALTY
        )

        _score = unknown_morphs_amount_score + min(tuning, MORPH_UNKNOWN_PENALTY - 1)

        # cap score to prevent 32-bit integer overflow
        self.due = self.score = min(_score, _MAX_SCORE)

        # Note: we have a whitespace before the <br> tags to avoid bugs
        self.score_terms = f"""
                unknown_morphs_amount_score: {unknown_morphs_amount_score}, <br>
                all_morphs_total_priority_score: {all_morphs_total_priority_score}, <br>
                unknown_morphs_total_priority_score: {unknown_morphs_total_priority_score}, <br>
                learning_morphs_total_priority_score: {learning_morphs_total_priority_score}, <br>
                all_morphs_avg_priority_score: {all_morphs_avg_priority_score}, <br>
                learning_morphs_avg_priority_score: {learning_morphs_avg_priority_score}, <br>
                leaning_morphs_target_difference_score: {leaning_morphs_target_difference_score}, <br>
                all_morphs_target_difference_score: {all_morphs_target_difference_score}
            """

        if _should_move_card_to_end(am_config, card_morph_metrics):
            self.due = _MAX_SCORE


def _should_move_card_to_end(
    am_config: AnkiMorphsConfig, card_morph_metrics: CardMorphsMetrics
) -> bool:
    if am_config.recalc_move_new_cards_to_the_end == am_globals.NEVER_OPTION:
        return False

    if am_config.recalc_move_new_cards_to_the_end == am_globals.ONLY_KNOWN_OPTION:
        if (
            len(card_morph_metrics.unknown_morphs) == 0
            and card_morph_metrics.num_learning_morphs == 0
        ):
            return True
    elif (
        am_config.recalc_move_new_cards_to_the_end
        == am_globals.ONLY_KNOWN_OR_FRESH_OPTION
    ):
        if len(card_morph_metrics.unknown_morphs) == 0:
            return True

    return False


def _get_all_morphs_target_difference(
    am_config: AnkiMorphsConfig, num_morphs: int
) -> int:
    high_target = am_config.algorithm_upper_target_all_morphs
    low_target = am_config.algorithm_lower_target_all_morphs
    coefficients_high = (
        am_config.algorithm_upper_target_all_morphs_coefficient_a,
        am_config.algorithm_upper_target_all_morphs_coefficient_b,
        am_config.algorithm_upper_target_all_morphs_coefficient_c,
    )
    coefficients_low = (
        am_config.algorithm_lower_target_all_morphs_coefficient_a,
        am_config.algorithm_lower_target_all_morphs_coefficient_b,
        am_config.algorithm_lower_target_all_morphs_coefficient_c,
    )
    return _get_morph_targets_difference(
        num_morphs=num_morphs,
        high_target=high_target,
        low_target=low_target,
        coefficients_high=coefficients_high,
        coefficients_low=coefficients_low,
    )


def _get_learning_morphs_target_difference(
    am_config: AnkiMorphsConfig, num_morphs: int
) -> int:
    high_target = am_config.algorithm_upper_target_learning_morphs
    low_target = am_config.algorithm_lower_target_learning_morphs
    coefficients_high = (
        am_config.algorithm_upper_target_learning_morphs_coefficient_a,
        am_config.algorithm_upper_target_learning_morphs_coefficient_b,
        am_config.algorithm_upper_target_learning_morphs_coefficient_c,
    )
    coefficients_low = (
        am_config.algorithm_lower_target_learning_morphs_coefficient_a,
        am_config.algorithm_lower_target_learning_morphs_coefficient_b,
        am_config.algorithm_lower_target_learning_morphs_coefficient_c,
    )
    return _get_morph_targets_difference(
        num_morphs=num_morphs,
        high_target=high_target,
        low_target=low_target,
        coefficients_high=coefficients_high,
        coefficients_low=coefficients_low,
    )


def _get_morph_targets_difference(
    num_morphs: int,
    high_target: int,
    low_target: int,
    coefficients_high: tuple[float, float, float],
    coefficients_low: tuple[float, float, float],
) -> int:
    if num_morphs > high_target:
        difference = abs(num_morphs - high_target)
        a, b, c = coefficients_high
    elif num_morphs < low_target:
        difference = abs(num_morphs - low_target)
        a, b, c = coefficients_low
    else:
        return 0

    # visualizing/playground: https://www.geogebra.org/graphing/ta3eqb8y
    return math.ceil(a * (difference**2) + b * difference + c)
