import pprint


class CardData:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        due: int,
        extra_field_unknowns: str,
        extra_field_unknowns_count: str,
        extra_field_highlighted: str,
        extra_field_score: str,
        extra_field_score_terms: str,
        tags: list[str],
    ):
        self.due = due
        self.extra_field_unknowns = extra_field_unknowns
        self.extra_field_unknowns_count = extra_field_unknowns_count
        self.extra_field_highlighted = extra_field_highlighted
        self.extra_field_score = extra_field_score
        self.extra_field_score_terms = extra_field_score_terms
        self.tags = tags

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, CardData)
        is_equal = True

        # use "if" for everything to get more feedback
        if self.due != other.due:
            print("Due mismatch!")
            is_equal = False

        if self.extra_field_unknowns != other.extra_field_unknowns:
            print("extra_field_unknowns mismatch!")
            is_equal = False

        if self.extra_field_unknowns_count != other.extra_field_unknowns_count:
            print("extra_field_unknowns_count mismatch!")
            is_equal = False

        if self.extra_field_highlighted != other.extra_field_highlighted:
            print("extra_field_highlighted mismatch!")
            is_equal = False

        if self.extra_field_score != other.extra_field_score:
            print("extra_field_score mismatch!")
            is_equal = False

        if self.tags != other.tags:
            print("tags mismatch!")
            is_equal = False

        if is_equal is False:
            print("self:")
            pprint.pp(vars(self))
            print("other:")
            pprint.pp(vars(other))

        return is_equal
