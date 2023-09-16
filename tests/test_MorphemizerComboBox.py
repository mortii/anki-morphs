import pytest
from aqt.qt import QApplication

from morph.UI import MorphemizerComboBox
from morph.morphemizer import getAllMorphemizers


@pytest.fixture(scope="module")  # module-scope: created and destroyed once per module. Cached.
def set_up_app():
    app = QApplication([])  # having an 'app' variable is necessary for MorphemizerComboBox() to work
    return app


def test_set_and_get_current(set_up_app):
    combobox = MorphemizerComboBox()
    combobox.setMorphemizers(getAllMorphemizers())
    combobox.setCurrentByName('MecabMorphemizer')
    assert combobox.currentText() == 'Japanese MorphMan'

    current = combobox.getCurrent()
    assert current.getDescription() == 'Japanese MorphMan'


def test_empty_morphemizer_list(set_up_app):
    combobox = MorphemizerComboBox()
    combobox.setMorphemizers([])
    combobox.setCurrentByName('AnyBecauseNothingExists')

    current = combobox.getCurrent()
    assert current is None
