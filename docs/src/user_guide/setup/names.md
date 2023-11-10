# Names

AnkiMorphs enables users to include a list of names in a file named names.txt, preventing them from being marked as
unknown. This feature is designed so users won't have to learn the names of places or individuals, as these words lack
inherent meaning that can be acquired.

To activate this feature, navigate to ``Tool > AnkiMorphs > Settings > Skip > Parse`` and tick the option ``Ignore names
found in "names.txt"``

![ignore-names-option.png](../../img/ignore-names-option.png)

To update the list of names, input a list of names separated by new lines into the names.txt file. The file can be found
in different locations based on your operating system:

- For Windows: ``%APPDATA%\Anki2\ProfileName``
- For MacOS: ``~/Library/Application``
- For Linux: ``~/.local/share/Anki2`` or ``$XDG_DATA_HOME/Anki2``

![example-name-list.png](../../img/example-name-list.png)

During a review, you can also add names to the list by selecting a word, right-clicking it, and choosing "Mark as name"
from the dropdown menu. And the word will automatically be added to names.txt.

![mark-as-name.png](../../img/mark-as-name.png)
