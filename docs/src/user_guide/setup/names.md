# Names

>**Note**:
>
>- **Memory Usage**: AnkiMorphs loads the entire list of names into memory and compares against it each time you review 
> a card. To avoid slowdowns, keep the list of names as small as possible.
>- **Loading Changes**: If you manually edit the `names.txt` file, you must restart Anki for the changes to take effect.
>However, if you use the `Mark as name` feature, no restart is required.

You can have AnkiMorphs automatically filter out specified names found on your cards. This feature is designed so users
won't have to learn the names of places or individuals, as these words lack
inherent meaning that can be acquired.

You can activate the feature by selecting `Ignore names found in names.txt` it in
the [preprocess settings](settings/preprocess.md).

The `names.txt` file is located in your [anki profile folder](../glossary.md#profile-folder).

![example-name-list.png](../../img/example-name-list.png)

You can either update this file manually, or during a review you can also add names to the list by selecting a word,
right-clicking it, and choosing `Mark as name` from the dropdown menu.

![mark-as-name.png](../../img/mark-as-name.png)

