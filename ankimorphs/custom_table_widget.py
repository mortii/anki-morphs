from aqt.qt import (  # pylint:disable=no-name-in-module
    QApplication,
    QKeySequence,
    QTableWidget,
)


class CustomTableWidget(QTableWidget):
    def keyPressEvent(self, event):  # pylint:disable=invalid-name
        if event.matches(QKeySequence.StandardKey.Copy):
            text = ""
            sel_range = self.selectionModel().selection().first()

            for y_value in range(sel_range.top(), sel_range.bottom() + 1):
                for x_value in range(sel_range.left(), sel_range.right() + 1):
                    if x_value != sel_range.left():
                        text += "\t"
                    text += str(self.item(y_value, x_value).text())
                text += "\n"

            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            event.accept()
            return
        super().keyPressEvent(event)
