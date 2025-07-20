from __future__ import annotations

from aqt.qt import (  # pylint:disable=no-name-in-module
    QMessageBox,
    QPushButton,
    QStyle,
    Qt,
    QWidget,
)


def show_info_box(title: str, body: str, parent: QWidget) -> None:
    info_box = QMessageBox(parent)
    info_box.setWindowTitle(title)
    info_box.setIcon(QMessageBox.Icon.Information)
    info_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    info_box.setTextFormat(Qt.TextFormat.MarkdownText)
    info_box.setText(body)
    info_box.exec()


def show_warning_box(title: str, body: str, parent: QWidget) -> bool:
    """
    Returns 'True' if user clicked 'Ok' button
    Returns 'False' otherwise.
    """
    warning_box = QMessageBox(parent)
    warning_box.setWindowTitle(title)
    warning_box.setIcon(QMessageBox.Icon.Warning)
    warning_box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    warning_box.setTextFormat(Qt.TextFormat.MarkdownText)
    warning_box.setText(body)

    answer: int = warning_box.exec()
    if answer == QMessageBox.StandardButton.Yes:
        return True
    return False


def show_discard_message_box(title: str, body: str, parent: QWidget) -> bool:
    style: QStyle | None = parent.style()
    assert style is not None

    discard_button = QPushButton("Discard")
    discard_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton)
    discard_button.setIcon(discard_icon)

    cancel_button = QPushButton("Cancel")
    cancel_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
    cancel_button.setIcon(cancel_icon)
    cancel_button.setAutoDefault(True)

    warning_box = QMessageBox(parent)
    warning_box.setWindowTitle(title)
    warning_box.setIcon(QMessageBox.Icon.Question)
    warning_box.setTextFormat(Qt.TextFormat.MarkdownText)
    warning_box.setText(body)

    warning_box.addButton(discard_button, QMessageBox.ButtonRole.DestructiveRole)
    warning_box.addButton(cancel_button, QMessageBox.ButtonRole.RejectRole)
    warning_box.setDefaultButton(cancel_button)

    warning_box.exec()
    clicked_button = warning_box.clickedButton()

    if warning_box.buttonRole(clicked_button) == QMessageBox.ButtonRole.DestructiveRole:
        return True
    return False


def show_error_box(title: str, body: str, parent: QWidget) -> int:
    critical_box = QMessageBox(parent)
    critical_box.setWindowTitle(title)
    critical_box.setIcon(QMessageBox.Icon.Critical)
    critical_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    critical_box.setText(body)
    critical_box.setTextFormat(Qt.TextFormat.MarkdownText)
    answer: int = critical_box.exec()
    return answer


def confirm_new_extra_fields_selection(parent: QWidget) -> bool:
    title = "AnkiMorphs Confirmation"
    text = (
        'New "extra fields" have been selected in the settings, which will cause a full upload of your card'
        " collection the next time you synchronize.\n\nAny reviews or changes made on other devices that have"
        " yet to be synchronized will be lost when a full upload takes place.\n\nDo you still want to continue?"
    )
    answer = show_warning_box(title, text, parent=parent)
    return answer
