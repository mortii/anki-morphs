# -*- coding: utf-8 -*-
import os

# from aqt.qt import QWidget, QFileDialog, QProgressBar, QLabel, QLineEdit
from anki.utils import is_mac
from PyQt6.QtCore import Qt  # pylint:disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint:disable=no-name-in-module
    QDialog,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .morphemes import MorphDb
from .morphemizer import get_all_morphemizers
from .preferences import get_preference as cfg
from .ui import MorphemizerComboBox
from .util import error_msg, info_msg, mk_btn, mw


def get_path(line_edit):  # LineEdit -> GUI ()
    path = QFileDialog.getOpenFileName(caption="Open db", directory=cfg("path_dbs"))[0]
    line_edit.setText(path)


def get_progress_widget():
    progress_widget = QWidget()
    progress_widget.setFixedSize(400, 70)
    progress_widget.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress_bar = QProgressBar(progress_widget)
    if is_mac:
        progress_bar.setFixedSize(380, 50)
    else:
        progress_bar.setFixedSize(390, 50)
    progress_bar.move(10, 10)
    per = QLabel(progress_bar)
    per.setAlignment(Qt.AlignmentFlag.AlignCenter)

    progress_widget.show()
    return progress_widget, progress_bar


class MorphMan(QDialog):  # pylint: disable=too-many-instance-attributes
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_a = None
        self.db_b = None
        self.path_a = None
        self.path_b = None
        self.mw = parent  # pylint: disable=invalid-name
        self.setWindowTitle("Morph Man 3 Manager")
        self.grid = grid = QGridLayout(self)
        self.vbox = vbox = QVBoxLayout()

        # DB Paths
        self.a_path_line_edit = QLineEdit()
        vbox.addWidget(self.a_path_line_edit)
        self.a_path_btn = mk_btn(
            "Browse for DB A", lambda le: get_path(self.a_path_line_edit), vbox
        )

        self.b_path_line_edit = QLineEdit()
        vbox.addWidget(self.b_path_line_edit)
        self.b_path_btn = mk_btn(
            "Browse for DB B", lambda le: get_path(self.b_path_line_edit), vbox
        )

        # Comparisons
        self.show_a_btn = mk_btn("A", self.on_show_a, vbox)
        self.a_minus_b_btn = mk_btn("A-B", lambda x: self.on_diff("A-B"), vbox)
        self.b_minus_a_btn = mk_btn("B-A", lambda x: self.on_diff("B-A"), vbox)
        self.sym_btn = mk_btn(
            "Symmetric Difference", lambda x: self.on_diff("sym"), vbox
        )
        self.inter_btn = mk_btn("Intersection", lambda x: self.on_diff("inter"), vbox)
        self.union_btn = mk_btn("Union", lambda x: self.on_diff("union"), vbox)

        # Creation
        # language class/morphemizer
        self.db = None  # pylint: disable=invalid-name
        self.morphemizer_combo_box = MorphemizerComboBox()
        self.morphemizer_combo_box.set_morphemizers(get_all_morphemizers())

        vbox.addSpacing(40)
        vbox.addWidget(self.morphemizer_combo_box)
        self.extract_txt_file_btn = mk_btn(
            "Extract morphemes from file", self.on_extract_txt_file, vbox
        )
        self.save_results_btn = mk_btn("Save results to db", self.on_save_results, vbox)

        # Display
        vbox.addSpacing(40)
        self.col_all_mode = QRadioButton("All result columns")
        self.col_all_mode.setChecked(True)
        self.col_one_mode = QRadioButton("One result column")
        self.col_all_mode.clicked.connect(self.col_mode_button_listener)
        self.col_one_mode.clicked.connect(self.col_mode_button_listener)
        vbox.addWidget(self.col_all_mode)
        vbox.addWidget(self.col_one_mode)
        self.morph_display = QTextEdit()
        self.analysis_display = QTextEdit()

        # layout
        grid.addLayout(vbox, 0, 0)
        grid.addWidget(self.morph_display, 0, 1)
        grid.addWidget(self.analysis_display, 0, 2)

    def load_a(self):
        self.path_b = self.a_path_line_edit.text()
        self.db_a = MorphDb(path=self.path_b)
        if not self.db:
            self.db = self.db_a

    def load_b(self):
        self.path_a = self.b_path_line_edit.text()
        self.db_b = MorphDb(path=self.path_a)

    def load_ab(self):
        self.load_a()
        self.load_b()

    def on_show_a(self):
        try:
            self.load_a()
        except Exception as error:
            return error_msg(f"Can't load db:\n{error}")
        self.db = self.db_a
        self.update_display()

    def on_diff(self, kind):
        try:
            self.load_ab()
        except Exception as error:
            return error_msg(f"Can't load dbs:\n{error}")

        a_set = set(self.db_a.db.keys())
        b_set = set(self.db_b.db.keys())
        if kind == "sym":
            _morphs = a_set.symmetric_difference(b_set)
        elif kind == "A-B":
            _morphs = a_set.difference(b_set)
        elif kind == "B-A":
            _morphs = b_set.difference(a_set)
        elif kind == "inter":
            _morphs = a_set.intersection(b_set)
        elif kind == "union":
            _morphs = a_set.union(b_set)
        else:
            raise ValueError(
                f"'kind' must be one of [sym, A-B, B-A, inter, union], it was actually '{kind}'"
            )

        self.db.clear()
        for _morph in _morphs:
            locs = set()
            if _morph in self.db_a.db:
                locs.update(self.db_a.db[_morph])
            if _morph in self.db_b.db:
                locs.update(self.db_b.db[_morph])
            self.db.update_morph_locs(_morph, locs)

        self.update_display()

    def on_extract_txt_file(self):
        src_path = QFileDialog.getOpenFileName(
            caption="Text file to extract from?", directory=cfg("path_dbs")
        )[0]
        if not src_path:
            return

        dest_path = QFileDialog.getSaveFileName(
            caption="Save morpheme db to?",
            directory=cfg("path_dbs") + os.sep + "textFile.db",
        )[0]
        if not dest_path:
            return

        mat = cfg("text file import maturity")
        db = MorphDb.mk_from_file(  # pylint:disable=invalid-name
            str(src_path), self.morphemizer_combo_box.get_current(), mat
        )
        if db:
            db.save(str(dest_path))
            info_msg("Extracted successfully")

    def on_save_results(self):
        dir_path = cfg("path_dbs") + os.sep + "results.db"
        dest_path = QFileDialog.getSaveFileName(
            caption="Save results to?", directory=dir_path
        )[0]
        if not dest_path:
            return
        if not hasattr(self, "db"):
            return error_msg("No results to save")
        self.db.save(str(dest_path))
        info_msg("Saved successfully")

    def col_mode_button_listener(self):
        col_mode_button = self.sender()
        if col_mode_button.isChecked():
            try:
                self.update_display()
            except AttributeError:
                return  # User has not selected a db view yet

    def update_display(self):
        if self.col_all_mode.isChecked():
            self.morph_display.setText(self.db.show_ms())
        else:
            self.morph_display.setText(
                "\n".join(sorted(list(set([m.norm for m in self.db.db]))))
            )
        self.analysis_display.setText(self.db.analyze2str())


def main():
    mw.mm = MorphMan(mw)
    mw.mm.show()
