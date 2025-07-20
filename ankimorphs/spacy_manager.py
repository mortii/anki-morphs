from __future__ import annotations

import sys
from typing import Callable

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (  # pylint:disable=no-name-in-module
    QColor,
    QDialog,
    QIcon,
    QListWidgetItem,
    QPixmap,
    QSize,
    QStyle,
)
from aqt.utils import tooltip

from . import ankimorphs_globals as am_globals
from . import message_box_utils
from .extra_settings import extra_settings_keys
from .extra_settings.ankimorphs_extra_settings import AnkiMorphsExtraSettings
from .morphemizers import spacy_wrapper
from .ui.spacy_manager_dialog_ui import Ui_SpacyManagerDialog


class SpacyManagerDialog(QDialog):
    def __init__(
        self,
    ) -> None:
        assert mw is not None

        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.ui = Ui_SpacyManagerDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        spacy_wrapper.load_spacy_modules()

        self._setup_labels()
        self._setup_buttons()
        self._setup_icons()
        self._setup_lists()

        self.am_extra_settings = AnkiMorphsExtraSettings()
        self.am_extra_settings.beginGroup(
            extra_settings_keys.Dialogs.SPACY_MANAGER_WINDOW
        )
        self._setup_geometry()
        self.am_extra_settings.endGroup()

        self.show()

    def _setup_labels(self) -> None:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        status = "is" if spacy_wrapper.successful_import else "is not"
        text = f"spaCy {status} installed for python {python_version}"
        self.ui.spacyInstallationStatusLabel.setText(text)

    def _setup_icons(self) -> None:
        style: QStyle | None = self.style()
        assert style is not None

        transparent_pixmap = QPixmap(16, 16)
        transparent_pixmap.fill(QColor(0, 0, 0, 0))  # Fully transparent

        self.transparent_icon = QIcon(transparent_pixmap)
        self.apply_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)

    def _setup_buttons(self) -> None:
        self.ui.spacyInstallPushButton.setAutoDefault(False)
        self.ui.purgeSpacyPushButton.setAutoDefault(False)
        self.ui.installModelPushButton.setAutoDefault(False)
        self.ui.deleteModelPushButton.setAutoDefault(False)

        if spacy_wrapper.successful_import:
            self.ui.purgeSpacyPushButton.setEnabled(True)
            self.ui.spacyInstallPushButton.setDisabled(True)

        else:
            self.ui.spacyInstallPushButton.setEnabled(True)
            self.ui.purgeSpacyPushButton.setDisabled(True)

        self.ui.installModelPushButton.setDisabled(True)
        self.ui.deleteModelPushButton.setDisabled(True)

        self.ui.spacyInstallPushButton.clicked.connect(self._on_install_spacy_clicked)
        self.ui.purgeSpacyPushButton.clicked.connect(self._on_purge_spacy_clicked)
        self.ui.installModelPushButton.clicked.connect(self._on_install_model_clicked)
        self.ui.deleteModelPushButton.clicked.connect(self._on_delete_model_clicked)

    def _on_install_spacy_clicked(self) -> None:
        title = "Install spaCy"
        body = "Are you sure you want to download and install spaCy?"
        answer = message_box_utils.show_warning_box(title=title, body=body, parent=self)

        if not answer:
            return

        def _on_success() -> None:
            mw.progress.finish()
            message_box_utils.show_info_box(
                title="Success", body="Please restart Anki to load spaCy", parent=self
            )

        self.ui.spacyInstallPushButton.setDisabled(True)
        mw.progress.start(label="Downloading & Installing spaCy")

        operation = QueryOp(
            parent=self,
            op=lambda _: spacy_wrapper.create_spacy_venv(),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_purge_spacy_clicked(self) -> None:
        title = "Purge spaCy"
        body = "Are you sure you want to uninstall spaCy and all models?"
        answer = message_box_utils.show_warning_box(title=title, body=body, parent=self)

        if not answer:
            return

        def _on_success() -> None:
            mw.progress.finish()
            self.ui.purgeSpacyPushButton.setDisabled(True)
            tooltip("Please restart Anki", period=5000, parent=self)

        operation = QueryOp(
            parent=self,
            op=lambda _: spacy_wrapper.delete_spacy_venv(),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_install_model_clicked(self) -> None:
        current_item: QListWidgetItem | None = self.ui.modelsListWidget.currentItem()
        assert current_item is not None

        _title = "Install model?"
        _body = f"Are you sure you want to download and install {current_item.text()}?"
        if not message_box_utils.show_warning_box(
            title=_title, body=_body, parent=self
        ):
            return

        def _on_success() -> None:
            mw.progress.finish()
            message_box_utils.show_info_box(
                title="Success",
                body="Please restart Anki to reload models",
                parent=self,
            )

        mw.progress.start(label=f"Downloading & Installing {current_item.text()}")
        operation = QueryOp(
            parent=self,
            op=lambda _: spacy_wrapper.install_model(current_item.text()),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_delete_model_clicked(self) -> None:
        current_item: QListWidgetItem | None = self.ui.modelsListWidget.currentItem()
        assert current_item is not None

        _title = "Delete model?"
        _body = f"Are you sure you want to delete {current_item.text()}?"
        if not message_box_utils.show_warning_box(
            title=_title, body=_body, parent=self
        ):
            return

        def _on_success() -> None:
            mw.progress.finish()
            message_box_utils.show_info_box(
                title="Success",
                body="Please restart Anki to reload models",
                parent=self,
            )

        mw.progress.start(label=f"Deleting {current_item.text()}")
        operation = QueryOp(
            parent=mw,
            op=lambda _: spacy_wrapper.uninstall_model(current_item.text()),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _setup_lists(self) -> None:
        self.ui.languagesListWidget.setIconSize(QSize(16, 16))
        self.ui.modelsListWidget.setIconSize(QSize(16, 16))

        self._populate_languages_list()

        self.ui.languagesListWidget.currentItemChanged.connect(
            self._populate_models_list
        )
        self.ui.modelsListWidget.currentItemChanged.connect(
            self._toggle_model_action_buttons
        )

        if not spacy_wrapper.successful_import:
            self.ui.languagesListWidget.setDisabled(True)
            self.ui.modelsListWidget.setDisabled(True)

    def _populate_languages_list(self) -> None:
        installed_models = set(spacy_wrapper.get_installed_models())

        for (
            lang,
            available_models,
        ) in spacy_wrapper.available_langs_and_models.items():

            item = QListWidgetItem(f"{lang}")

            if not installed_models.isdisjoint(available_models):
                # language has installed model(s)
                item.setIcon(self.apply_icon)
            else:
                item.setIcon(self.transparent_icon)  # to maintain text alignment

            self.ui.languagesListWidget.addItem(item)

    def _populate_models_list(
        self,
        current_lang: QListWidgetItem | None,
        _previous_lang: QListWidgetItem | None,
    ) -> None:
        self.ui.modelsListWidget.clear()  # remove previous entries

        if current_lang is not None:
            # NB! don't use a set for available_models, it randomizes the
            # order when adding them as items later
            available_models = spacy_wrapper.available_langs_and_models[
                current_lang.text()
            ]
            installed_models: set[str] = set(spacy_wrapper.get_installed_models())

            for available_model in available_models:
                item = QListWidgetItem(available_model)

                if available_model in installed_models:
                    item.setIcon(self.apply_icon)
                else:
                    item.setIcon(self.transparent_icon)  # to maintain text alignment

                self.ui.modelsListWidget.addItem(item)

    def _toggle_model_action_buttons(
        self,
        current_model: QListWidgetItem | None,
        _previous_model: QListWidgetItem | None,
    ) -> None:
        if current_model is not None:
            current_item: QListWidgetItem | None = (
                self.ui.modelsListWidget.currentItem()
            )
            assert current_item is not None

            if current_item.icon().cacheKey() == self.apply_icon.cacheKey():
                # model is already installed
                self.ui.installModelPushButton.setDisabled(True)
                self.ui.deleteModelPushButton.setEnabled(True)
            else:
                # model is not installed
                self.ui.installModelPushButton.setEnabled(True)
                self.ui.deleteModelPushButton.setDisabled(True)
        else:
            self.ui.installModelPushButton.setDisabled(True)
            self.ui.deleteModelPushButton.setDisabled(True)

    def _setup_geometry(self) -> None:
        stored_geometry = self.am_extra_settings.value(
            extra_settings_keys.SpacyManagerWindowKeys.WINDOW_GEOMETRY
        )
        if stored_geometry is not None:
            self.restoreGeometry(stored_geometry)

    def _on_failure(self, failure: Exception) -> None:
        mw.progress.finish()
        message_box_utils.show_error_box(
            title="Error",
            body=f"{failure}",
            parent=self,
        )

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.am_extra_settings.spacy_manager_window_settings(
            geometry=self.saveGeometry()
        )
        self.close()
        aqt.dialogs.markClosed(am_globals.SPACY_MANAGER_DIALOG_NAME)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()
