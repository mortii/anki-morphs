from aqt.qt import QComboBox


class MorphemizerComboBox(QComboBox):
    def setMorphemizers(self, morphemizers):
        if type(morphemizers) == list:
            self.morphemizers = morphemizers
        else:
            self.morphemizers = []

        for morphemizer in self.morphemizers:
            self.addItem(morphemizer.get_description())

        self.setCurrentIndex(0)

    def get_current(self):
        try:
            return self.morphemizers[self.currentIndex()]
        except IndexError:
            return None

    def set_current_by_name(self, name):
        active = False
        for i, morphemizer in enumerate(self.morphemizers):
            if morphemizer.get_name() == name:
                active = i
        if active:
            self.setCurrentIndex(active)
