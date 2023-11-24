# Prioritizing

The more frequently a morph occurs in a language, the more useful it is to learn. This is the fundamental principle
behind AnkiMorphs--learn a language in the order that will be the most useful.

AnkiMorphs is a general purpose language learning tool, therefore it has to be told which morphs occur most often. You
can do this in two ways, either have AnkiMorphs calculate the morph frequencies found in your
cards (`Collection frequency`), or you can specify a [custom .csv file](#frequencycsv) that contains that information.

## frequency.csv

![frequency-csv.png](../../img/frequency-csv.png)

Your custom .csv file needs to follow this format:

- The 1st row is assumed to contain column headers and will be ignored.
- Rows 2 and down are assumed to contain morphs in descending order of frequency, i.e. the morph on the 2nd row is the
  most occurring morph, the morph on the 3rd row is the second most occurring, etc.

Keep the files to 50K rows or less, any rows after that are ignored for practical purposes.

Any .csv file located in the folder [[anki profile folder](../glossary.md#profile-folder)]`/frequency-files/` is
available for selection in [note filters](../setup/settings/note-filter.md).

### Creating Your Own frequency.csv

You can also use the [Frequency File Generator](../usage/frequency-file-generator.md) to generate your own frequency.csv
file.

### Downloadable frequency.csv files

If you have [generated a frequency file](../usage/frequency-file-generator.md) that you think other people might benefit
from using then please consider sharing
it! Create a new ['Documentation request' issue](https://github.com/mortii/anki-morphs/issues/new/choose) where you let
me
know, and I'll add it to the lists below.

<details>
  <summary>Japanese Frequency Lists</summary>


> * <a download href="../../frequency_lists/japanese_frequency_lists/nanako-25k/jp_frequency.csv">nanako 25k</a>  
    Created from [NanakoRaws-Anime-Japanese-subtitles](https://github.com/kienkzz/NanakoRaws-Anime-Japanese-subtitles)


</details>

<details>
  <summary>Chinese Frequency Lists</summary>

> *
</details>

