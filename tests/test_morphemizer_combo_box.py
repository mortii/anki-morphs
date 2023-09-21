from ankimorphs.morphemizer import get_all_morphemizers
from ankimorphs.UI import MorphemizerComboBox


def test_set_and_get_current(qtbot):
    combobox = MorphemizerComboBox()
    qtbot.addWidget(combobox)
    combobox.setMorphemizers(get_all_morphemizers())
    combobox.set_current_by_name("MecabMorphemizer")
    assert combobox.currentText() == "Japanese MorphMan"

    current = combobox.get_current()
    assert current.get_description() == "Japanese MorphMan"


def test_empty_morphemizer_list(qtbot):
    combobox = MorphemizerComboBox()
    qtbot.addWidget(combobox)
    combobox.setMorphemizers([])
    combobox.set_current_by_name("AnyBecauseNothingExists")

    current = combobox.get_current()
    assert current is None
