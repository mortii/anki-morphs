from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme

# Anki stores the 'due' value of cards as a 32-bit integer
# on the backend, with '2147483647' being the max value before
# overflow. To prevent overflow when cards are repositioned,
# we decrement the second digit (from the left) of the max value,
# which should give plenty of leeway (10^8).
_DEFAULT_SCORE: int = 2_047_483_647

morph_unknown_penalty: int = 1_000_000


class ScoreValues:
    def __init__(
        self,
        card_score: int,
        card_unknown_morphs: list[Morpheme],
        card_has_learning_morphs: bool,
        score_terms: str = "N/A",
    ):
        self.card_score = card_score
        self.card_unknown_morphs = card_unknown_morphs
        self.card_has_learning_morphs = card_has_learning_morphs
        self.score_terms = score_terms


####################################################################################
#                                      ALGORITHM
####################################################################################
# The algorithm is calculated with the following equation
#
#     score = (
#             unknown_morphs_total_priority_score
#             + all_morphs_avg_priority_score
#             + all_morphs_total_priority_score
#             + leaning_morphs_target_difference_score
#             + all_morphs_target_difference_score
#     )
#
# Each of the terms has an associated weight that can be used to bias
# the term arbitrarily, e.g.:
#
#     unknown_morphs_total_priority_score = (
#             TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT * total_priority_unknown_morphs
#     )
#
# A lower total score means that the card will show up sooner
# in the new card list, so each of the factors can be thought
# of as a penalty.
#
# Priority is measured by frequency of the morph. An unknown morph
# that has a higher frequency will have a lower priority score
#
# TERMS IN THE ALGORITHM:
#
# - unknown_morphs_total_priority_score:
#   The sum of the priority scores for all the unknown morphs.
#   Note: We only implement a "total priority" version since cards should ideally
#   only contain one unknown morph.
#
# - all_morphs_avg_priority_score:
#   The average (mean) of the priority scores for all found morphs.
#
# - all_morphs_total_priority_score:
#   The total priority scores for all found morphs
#
# - leaning_morphs_target_difference_score:
#   The penalty given when the target number of learning morphs is not reached.
#   This is used as a means of reinforcing new vocabulary.
#   A piecewise quadratic equation is used for more flexibility, i.e. the punishment
#   can be higher for overshooting the target vs undershooting, and vice-versa.
#
# - all_morphs_target_difference_score:
#   Same as "leaning_morphs_target_difference_score", but for all morphs.
#
#######################################
# todo: turn these into documentation/comments
# # The following should be user selected
# # Target length of sentences
# TARGET_NUM_MORPHS_LOW = 4
# TARGET_NUM_MORPHS_HIGH = 6
#
# TARGET_NUM_LEARNING_MORPHS_LOW = 1
# TARGET_NUM_LEARNING_MORPHS_HIGH = 2
#
# # quadratic equation coefficients: ax^2 + bx + c
# TARGET_NUM_MORPHS_HIGH_COEFFICIENTS = (1, 0, 0)
# TARGET_NUM_MORPHS_LOW_COEFFICIENTS = (0, 1, 0)
#
# TARGET_NUM_LEARNING_HIGH_COEFFICIENTS = (1, 0, 0)
# TARGET_NUM_LEARNING_LOW_COEFFICIENTS = (1, 0, 0)

# # Weights for the different criteria
# TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT = 10
# AVG_PRIORITY_ALL_MORPHS_WEIGHT = 1
# TOTAL_PRIORITY_ALL_MORPHS_WEIGHT = 0
# LEARNING_MORPHS_TARGET_DISTANCE_WEIGHT = 5
# ALL_MORPHS_TARGET_DISTANCE_WEIGHT = 1
#######################################


def get_card_score_values(  # pylint:disable=too-many-locals, too-many-statements, too-many-branches
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[Morpheme]],
    morph_priorities: dict[str, int],
) -> ScoreValues:

    unknown_morphs: list[Morpheme] = []
    no_morph_priority_value = len(morph_priorities) + 1
    has_learning_morph: bool = False

    try:
        card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        # return _DEFAULT_SCORE, unknown_morphs, has_learning_morph
        return ScoreValues(
            card_score=_DEFAULT_SCORE,
            card_unknown_morphs=unknown_morphs,
            card_has_learning_morphs=has_learning_morph,
        )

    total_priority_unknown_morphs = 0
    total_priority_all_morphs = 0
    num_learning_morphs = 0

    # todo: make this a separate function
    for morph in card_morphs:
        # print(f"morph: {morph}")

        assert morph.highest_inflection_learning_interval is not None

        morph_priority = no_morph_priority_value

        if am_config.algorithm_lemma_priority:
            key = morph.lemma + morph.lemma
            if key in morph_priorities:
                morph_priority = morph_priorities[key]
        else:
            key = morph.lemma + morph.inflection
            if key in morph_priorities:
                morph_priority = morph_priorities[key]

        # print(
        #     f"inflection: {morph.inflection}, lemma: {morph.lemma}, priority: {morph_priority}"
        # )

        total_priority_all_morphs += morph_priority

        if am_config.algorithm_lemma_priority:
            assert morph.highest_lemma_learning_interval is not None

            if morph.highest_lemma_learning_interval == 0:
                unknown_morphs.append(morph)
                total_priority_unknown_morphs += morph_priority

            elif (
                morph.highest_lemma_learning_interval
                < am_config.recalc_interval_for_known
            ):
                has_learning_morph = True
                num_learning_morphs += 1

        else:
            if morph.highest_inflection_learning_interval == 0:
                unknown_morphs.append(morph)
                total_priority_unknown_morphs += morph_priority

            elif (
                morph.highest_inflection_learning_interval
                < am_config.recalc_interval_for_known
            ):
                has_learning_morph = True
                num_learning_morphs += 1

    if len(unknown_morphs) == 0 and am_config.recalc_move_known_new_cards_to_the_end:
        # Move stale cards to the end of the queue
        # return _DEFAULT_SCORE, unknown_morphs, has_learning_morph
        return ScoreValues(
            card_score=_DEFAULT_SCORE,
            card_unknown_morphs=unknown_morphs,
            card_has_learning_morphs=has_learning_morph,
        )

    all_morphs_target_difference: int = _get_all_morphs_target_difference(
        am_config=am_config,
        num_morphs=len(card_morphs),
    )

    learning_morphs_target_difference: int = _get_learning_morphs_target_difference(
        am_config=am_config,
        num_morphs=num_learning_morphs,
    )

    all_morphs_avg_priority = int(total_priority_all_morphs / len(card_morphs))

    unknown_morphs_total_priority_score = (
        am_config.algorithm_total_priority_unknown_morphs
        * total_priority_unknown_morphs
    )
    all_morphs_avg_priority_score = (
        am_config.algorithm_average_priority_all_morphs * all_morphs_avg_priority
    )
    all_morphs_total_priority_score = (
        am_config.algorithm_total_priority_all_morphs * total_priority_all_morphs
    )
    leaning_morphs_target_difference_score = (
        am_config.algorithm_learning_morphs_target_distance
        * learning_morphs_target_difference
    )
    all_morphs_target_difference_score = (
        am_config.algorithm_all_morphs_target_distance * all_morphs_target_difference
    )

    score = (
        unknown_morphs_total_priority_score
        + all_morphs_avg_priority_score
        + all_morphs_total_priority_score
        + leaning_morphs_target_difference_score
        + all_morphs_target_difference_score
    )

    if score >= morph_unknown_penalty:
        # Cap morph priority penalties as described in #(2.2)
        score = morph_unknown_penalty - 1

    unknown_morphs_amount_score = len(unknown_morphs) * morph_unknown_penalty
    score += unknown_morphs_amount_score

    # cap score to prevent 32-bit integer overflow
    score = min(score, _DEFAULT_SCORE)

    # print(f"card id: {card_id}")
    # print(f"card_morphs_inflections: {[morph.inflection for morph in card_morphs]}")
    # print(f"unknown_morphs: {len(unknown_morphs)}")
    # print(f"learning_morphs: {num_learning_morphs}")
    # print(f"unknown_morphs_amount_score: {unknown_morphs_amount_score}")
    # print(f"unknown_morphs_total_priority_score: {unknown_morphs_total_priority_score}")
    # print(f"all_morphs_avg_priority_score: {all_morphs_avg_priority_score}")
    # print(f"all_morphs_total_priority_score: {all_morphs_total_priority_score}")
    # print(
    #     f"leaning_morphs_target_difference_score: {leaning_morphs_target_difference_score}"
    # )
    # print(f"all_morphs_target_difference_score: {all_morphs_target_difference_score}")
    # print(f"score: {score}")
    # print()

    score_terms: str = f"""
        unknown_morphs_amount_score: {unknown_morphs_amount_score},<br>
        unknown_morphs_total_priority_score: {unknown_morphs_total_priority_score},<br>
        all_morphs_avg_priority_score: {all_morphs_avg_priority_score},<br>
        all_morphs_total_priority_score: {all_morphs_total_priority_score},<br>
        leaning_morphs_target_difference_score: {leaning_morphs_target_difference_score},<br>
        all_morphs_target_difference_score: {all_morphs_target_difference_score}
    """

    # return score, unknown_morphs, has_learning_morph
    return ScoreValues(
        card_score=score,
        card_unknown_morphs=unknown_morphs,
        card_has_learning_morphs=has_learning_morph,
        score_terms=score_terms,
    )


def _get_morph_targets_difference(
    num_morphs: int,
    high_target: int,
    low_target: int,
    coefficients_high: tuple[int, int, int],
    coefficients_low: tuple[int, int, int],
) -> int:
    if num_morphs > high_target:
        difference = abs(num_morphs - high_target)
        a, b, c = coefficients_high
    elif num_morphs < low_target:
        difference = abs(num_morphs - low_target)
        a, b, c = coefficients_low
    else:
        return 0

    # https://www.geogebra.org/graphing/ta3eqb8y
    return a * (difference**2) + b * difference + c


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
