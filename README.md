# AnkiMorphs

<a title="Rate on AnkiWeb" href="https://ankiweb.net/shared/info/900801631"><img src="https://glutanimate.com/logos/ankiweb-rate.svg"></a>
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.org/project/isort/)
[![Test and Lintt](https://github.com/mortii/anki-morphs/actions/workflows/build.yml/badge.svg)](https://github.com/mortii/anki-morphs/actions/workflows/build.yml)
[![Github Pages](https://github.com/mortii/anki-morphs/actions/workflows/deploy.yml/badge.svg)](https://github.com/mortii/anki-morphs/actions/workflows/deploy.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
<br>
<br>
MorphMan is an Anki addon that tracks what words you know, and utilizes that information to optimally reorder language cards. This
**greatly** optimizes your learning queue, as you will only see sentences with exactly one unknown word (see
[i+1 principle](https://massimmersionapproach.com/table-of-contents/anki/morphman/#glossary) for a more detailed explanation).

Install MorphMan via [AnkiWeb](https://ankiweb.net/shared/info/900801631)

MorphMan supports the following languages:

- languages with spaces: **English**, **Russian**, **Spanish**, **Korean**, **Hindi**, **etc.**
- **Japanese**: You must additionally install the _[Japanese Support](https://ankiweb.net/shared/info/3918629684)_ Anki addon
- **Chinese**: For Anki 2.0, please use [Jieba-Morph](https://github.com/NinKenDo64/Jieba-Morph). Chinese is included in Morphman for Anki 2.1
- **CJK Characters**: Morphemizer that splits sentence into characters and filters for Chinese-Japanese-Korean logographic/idiographic characters.
- more languages can be added on request if morpheme-splitting-tools are available for it


