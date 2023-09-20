from ankimorphs.morphemizer import getAllMorphemizers
from ankimorphs.UI import MorphemizerComboBox


def test_set_and_get_current(qtbot):
    combobox = MorphemizerComboBox()
    qtbot.addWidget(combobox)
    combobox.setMorphemizers(getAllMorphemizers())
    combobox.setCurrentByName("MecabMorphemizer")
    assert combobox.currentText() == "Japanese MorphMan"

    current = combobox.getCurrent()
    assert current.getDescription() == "Japanese MorphMan"


def test_empty_morphemizer_list(qtbot):
    combobox = MorphemizerComboBox()
    qtbot.addWidget(combobox)
    combobox.setMorphemizers([])
    combobox.setCurrentByName("AnyBecauseNothingExists")

    current = combobox.getCurrent()
    assert current is None
