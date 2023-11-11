from typing import Optional

from aqt import mw
from aqt.qt import QDialog, QMainWindow  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from .morphemizer import Morphemizer, get_all_morphemizers
from .ui.frequency_file_generator_ui import Ui_FrequencyFileGeneratorDialog


def main() -> None:
    mw.ankimorphs_frequency_file_generator = FrequencyFileGeneratorDialog(mw)  # type: ignore[union-attr]
    mw.ankimorphs_frequency_file_generator.exec()  # type: ignore[union-attr]


class FrequencyFileGeneratorDialog(QDialog):
    # The UI comes from ankimorphs/ui/frequency_file_generator.ui which is used in Qt Designer,
    # which is then converted to ankimorphs/ui/frequency_file_generator_ui.py,
    # which is then imported here.
    #
    # Here we make the final adjustments that can't be made (or are hard to make) in
    # Qt Designer, like setting up tables and widget-connections.

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        assert mw
        self.mw = parent  # pylint:disable=invalid-name
        self.ui = Ui_FrequencyFileGeneratorDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self._morphemizers = get_all_morphemizers()
        self._populate_morphemizers()
        self._setup_buttons()

    def _populate_morphemizers(self) -> None:
        morphemizers: list[Morphemizer] = get_all_morphemizers()
        morphemizer_names = [mizer.get_description() for mizer in morphemizers]
        morphemizers_cbox = self.ui.comboBox
        morphemizers_cbox.addItems(morphemizer_names)

    def _setup_buttons(self) -> None:
        self.ui.inputButton.clicked.connect(self._on_input_button_clicked)
        self.ui.outputButton.clicked.connect(self._on_output_button_clicked)
        self.ui.createFrequencyFileButton.clicked.connect(self._generate_freqyency_file)

    def _on_input_button_clicked(self) -> None:
        # TODO:
        #  - we should ideally be able to select a directory OR a single file

        tooltip("clicked select input button", parent=mw)

    def _on_output_button_clicked(self) -> None:
        # TODO: should the user only be able to select a output
        #   directory or should they be able to set the file name too?

        tooltip("clicked select output button", parent=mw)

    def _generate_freqyency_file(self) -> None:
        # TODO:
        #  - we need to use a QueryOp to run this in the background
        #    like we do in recalc

        tooltip("clicked create frequency file button", parent=mw)
