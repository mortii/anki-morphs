# Installation

You can download the latest version of AnkiMorphs from [ankiweb](https://ankiweb.net/shared/info/472573498). You can
find
previous versions [on github releases](https://github.com/mortii/anki-morphs/releases).

AnkiMorphs parses text into morphs by using external morphemizers, and different languages will require different
morphemizers. Below are the currently supported morphemizers:

<details>
  <summary>Japanese morphemizers</summary>

> Japanese has two available morphemizers:
>
>- [MeCab](https://en.wikipedia.org/wiki/MeCab) morphemizer (recommended)  
   This can be added by installing the [ankimorphs-japanese-mecab](https://ankiweb.net/shared/info/1974309724) companion
   add-on (installation code: `1974309724`). Once this add-on has been installed and Anki has been restarted, the
   morphemizer will show up as the option `AnkiMorphs: Japanese`
>
>- [install spaCy](installation/installing-spacy.md) with Japanese models

</details>

<details>
  <summary>Chinese morphemizers</summary>

> Chinese has two available morphemizers:
>
>- [Jieba](https://github.com/fxsjy/jieba?tab=readme-ov-file#jieba-1) morphemizer (recommended)  
   This can be added by installing the [ankimorphs-chinese-jieba](https://ankiweb.net/shared/info/1857311956) companion
   add-on (installation code: `1857311956`). Once this add-on has been installed and Anki has been restarted, the
   morphemizer will show up as the option `AnkiMorphs: Chinese`
>
>- [install spaCy](installation/installing-spacy.md) with Chinese models

</details>

<details>
  <summary>Morphemizers for other languages</summary>

> For other languages you can [install spaCy](installation/installing-spacy.md), which currently supports:
>
>Catalan, Chinese, Croatian, Danish, Dutch, English, Finnish, French, German, Greek (Modern), Italian, Japanese, Korean,
> Lithuanian, Macedonian, Norwegian (Bokmål), Polish, Portuguese, Romanian, Russian, Slovenian, Spanish, Swedish,
> Ukrainian.
</details>

After the installation is complete, some [setup](setup.md) is required to get AnkiMorphs to work. After that you can
run [Recalc](usage/recalc.md) and you will be good to go!

[Here is an overview](installation/changes-to-anki.md) of the changes that are made to Anki after installing AnkiMorphs.