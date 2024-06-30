import pprint

from anki.cards import Card
from anki.notes import Note


class CardData:

    def __init__(
        self,
        card: Card,
        note: Note,
        field_positions: dict[str, int],
    ):

        self.due = card.due
        self.tags = note.tags

        for field, pos in field_positions.items():
            setattr(self, field, note.fields[pos])

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, CardData)
        is_equal = True

        for field in self.__dict__:
            # print(f"field: {field}")
            # print(f"getattr(self, field): {getattr(self, field)}")
            # print(f"getattr(other, field): {getattr(other, field)}")
            if getattr(self, field) != getattr(other, field):
                print(f"{field} mismatch")
                is_equal = False
        # assert False

        if not is_equal:
            print("self:")
            pprint.pp(vars(self))
            print("other:")
            pprint.pp(vars(other))

        return is_equal
