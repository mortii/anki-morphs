from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme

# Anki stores the 'due' value of cards as a 32-bit integer
# on the backend, with '2147483647' being the max value before
# overflow. To prevent overflow when cards are repositioned,
# we decrement the second digit (from the left) of the max value,
# which should give plenty of leeway (10^8).
_DEFAULT_SCORE: int = 2_047_483_647


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
# The following should be user selected
# Target length of sentences
TARGET_NUM_MORPHS_LOW = 4
TARGET_NUM_MORPHS_HIGH = 6

TARGET_NUM_LEARNING_MORPHS_LOW = 1
TARGET_NUM_LEARNING_MORPHS_HIGH = 2

# quadratic equation coefficients: ax^2 + bx + c
TARGET_NUM_MORPHS_HIGH_COEFFICIENTS = (1, 0, 0)
TARGET_NUM_MORPHS_LOW_COEFFICIENTS = (0, 1, 0)

TARGET_NUM_LEARNING_HIGH_COEFFICIENTS = (1, 0, 0)
TARGET_NUM_LEARNING_LOW_COEFFICIENTS = (1, 0, 0)

# Weights for the different criteria
TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT = 10
AVG_PRIORITY_ALL_MORPHS_WEIGHT = 1
TOTAL_PRIORITY_ALL_MORPHS_WEIGHT = 0
LEARNING_MORPHS_TARGET_DISTANCE_WEIGHT = 5
ALL_MORPHS_TARGET_DISTANCE_WEIGHT = 1
#######################################


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


def get_card_score_and_unknowns_and_learning_status(  # pylint:disable=too-many-locals, too-many-statements
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[Morpheme]],
    morph_priority: dict[str, int],  # todo: maybe name it frequency instead?
) -> tuple[int, list[Morpheme], bool]:

    morph_unknown_penalty: int = 1_000_000
    unknown_morphs: list[Morpheme] = []
    no_morph_priority_value = len(morph_priority) + 1
    has_learning_morph: bool = False

    try:
        card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return _DEFAULT_SCORE, unknown_morphs, has_learning_morph

    total_priority_unknown_morphs = 0
    num_learning_morphs = 0
    total_priority_all_morphs = 0

    for morph in card_morphs:
        assert morph.highest_learning_interval is not None

        print(
            f"morph: {morph.inflection}, priority: {morph_priority[morph.lemma_and_inflection] if morph.lemma_and_inflection in morph_priority else no_morph_priority_value}"
        )

        if morph.highest_learning_interval == 0:
            unknown_morphs.append(morph)
            if morph.lemma_and_inflection in morph_priority:
                total_priority_unknown_morphs += morph_priority[
                    morph.lemma_and_inflection
                ]
            else:
                total_priority_unknown_morphs += no_morph_priority_value

        elif morph.highest_learning_interval < am_config.recalc_interval_for_known:
            has_learning_morph = True
            num_learning_morphs += 1

        if morph.lemma_and_inflection not in morph_priority:
            # Heavily penalizes if a morph is not in frequency file
            total_priority_all_morphs = no_morph_priority_value
        else:
            total_priority_all_morphs += morph_priority[morph.lemma_and_inflection]

    if len(unknown_morphs) == 0 and am_config.recalc_move_known_new_cards_to_the_end:
        # Move stale cards to the end of the queue
        return _DEFAULT_SCORE, unknown_morphs, has_learning_morph

    all_morphs_target_difference: int = _get_morph_targets_difference(
        num_morphs=len(card_morphs),
        high_target=TARGET_NUM_MORPHS_HIGH,
        low_target=TARGET_NUM_MORPHS_LOW,
        coefficients_high=TARGET_NUM_MORPHS_HIGH_COEFFICIENTS,
        coefficients_low=TARGET_NUM_MORPHS_LOW_COEFFICIENTS,
    )
    learning_morphs_target_difference: int = _get_morph_targets_difference(
        num_morphs=num_learning_morphs,
        high_target=TARGET_NUM_LEARNING_MORPHS_HIGH,
        low_target=TARGET_NUM_LEARNING_MORPHS_LOW,
        coefficients_high=TARGET_NUM_LEARNING_HIGH_COEFFICIENTS,
        coefficients_low=TARGET_NUM_LEARNING_LOW_COEFFICIENTS,
    )
    all_morphs_avg_priority = int(total_priority_all_morphs / len(card_morphs))

    unknown_morphs_total_priority_score = (
        TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT * total_priority_unknown_morphs
    )
    all_morphs_avg_priority_score = (
        AVG_PRIORITY_ALL_MORPHS_WEIGHT * all_morphs_avg_priority
    )
    all_morphs_total_priority_score = (
        TOTAL_PRIORITY_ALL_MORPHS_WEIGHT * total_priority_all_morphs
    )
    leaning_morphs_target_difference_score = (
        LEARNING_MORPHS_TARGET_DISTANCE_WEIGHT * learning_morphs_target_difference
    )
    all_morphs_target_difference_score = (
        ALL_MORPHS_TARGET_DISTANCE_WEIGHT * all_morphs_target_difference
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

    print()
    print(f"card id: {card_id}")
    print(f"card_morphs: {[morph.inflection for morph in card_morphs]}")
    print(f"unknown_morphs: {len(unknown_morphs)}")
    print(f"learning_morphs: {num_learning_morphs}")
    print(f"unknown_morphs_amount_score: {unknown_morphs_amount_score}")
    print(f"unknown_morphs_total_priority_score: {unknown_morphs_total_priority_score}")
    print(f"all_morphs_avg_priority_score: {all_morphs_avg_priority_score}")
    print(f"all_morphs_total_priority_score: {all_morphs_total_priority_score}")
    print(
        f"leaning_morphs_target_difference_score: {leaning_morphs_target_difference_score}"
    )
    print(f"all_morphs_target_difference_score: {all_morphs_target_difference_score}")
    print(f"score: {score}")

    return score, unknown_morphs, has_learning_morph
