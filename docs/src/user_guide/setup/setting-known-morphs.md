# Setting Known Morphs

AnkiMorphs determines which morphs you know by analyzing the cards you specify. However, if you delete any of those
cards then it can lead to loss of information. To address this issue, you can store known morphs in .csv files in the
[[anki profile](../glossary.md#profile-folder)]`/known-morphs` folder.

![known-morphs-folder.png](../../img/known-morphs-folder.png)

Any .csv file that has the [priority file format](prioritizing.md#custom-priority-files) (like those produces by the
[Known Morphs Exporter](../usage/known-morphs-exporter.md)), and is placed within this folder, can be read during [Recalc](../usage/recalc.md) and saved to the database.

You can activate this feature by selecting `Read files in 'known-morphs' folder and register morphs as known`
in the [general settings tab](../setup/settings/general.md).