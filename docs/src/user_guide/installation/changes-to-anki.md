# Changes To Anki

After installing AnkiMorphs you will find that some changes have been made to Anki.

## Toolbar

![toolbar.png](../../img/toolbar.png)

The toolbar now has three new items:
- [Recalc](../usage/recalc.md)
- “U”, which stands for Known Unique Morphs
- "A", which stands for All Known Morphs

For some languages, U and A will always have the same number, but languages like japanese can have morphs with multiple
variations, and then they will eventually differ.

<details>
  <summary style="display:list-item"> Examples </summary>


<blockquote>

**Each column in the table contains variations of the same morph.**

Knowing the morph in the highlighted cell below would give you U: 1 and A: 1
<div class='morph-variation'>
<table>
    <colgroup>
    <col>
    <col>
    <col>
  </colgroup>
<tr>
    <td>ない</td>
    <td>物</td>
    <td>奴</td>
    <td>出</td>
</tr>
<tr>
    <td>ねぇ</td>
    <td>もの</td>
    <td>やつ</td>
    <td>出る</td>
</tr>
<tr>
    <td>ね</td>
    <td class="morph-variation-selected_cell">もん</td>
    <td>ヤツ</td>
    <td>出よう</td>
</tr>
</table>
</div>

Knowing the morphs in the highlighted cells below would give you U: 1 and A: 2

<div class='morph-variation'>
<table>
    <colgroup>
    <col>
    <col>
    <col>
  </colgroup>
<tr>
    <td>ない</td>
    <td class="morph-variation-selected_cell">物</td>
    <td>奴</td>
    <td>出</td>
</tr>
<tr>
    <td>ねぇ</td>
    <td>もの</td>
    <td>やつ</td>
    <td>出る</td>
</tr>
<tr>
    <td>ね</td>
    <td class="morph-variation-selected_cell">もん</td>
    <td>ヤツ</td>
    <td>出よう</td>
</tr>
</table>
</div>

Knowing the morphs in the highlighted cells below would give you U: 2 and A: 3

<div class='morph-variation'>
<table>
    <colgroup>
    <col>
    <col>
    <col>
  </colgroup>
<tr>
    <td>ない</td>
    <td class="morph-variation-selected_cell">物</td>
    <td>奴</td>
    <td>出</td>
</tr>
<tr>
    <td>ねぇ</td>
    <td>もの</td>
    <td>やつ</td>
    <td class="morph-variation-selected_cell">出る</td>
</tr>
<tr>
    <td>ね</td>
    <td class="morph-variation-selected_cell">もん</td>
    <td>ヤツ</td>
    <td>出よう</td>
</tr>
</table>
</div>
<br>
</blockquote>
</details>



The U and A numbers are updated after every [Recalc](../usage/recalc.md).

## Browse

AnkiMorphs adds new options in the Browse window that can be accessed either from the "AnkiMorphs" menu at the top or when
right-clicking cards:

* “View Morphemes”
* “Learn Card Now”
* “Browse Same Morphs”
* “Tag As Known”

These features are explained in [here](../usage/browser.md).

## Tools Menu

A AnkiMorphs menu is added to "Tools" menu and has the options:

* [“Settings”](../setup/settings.md)
* [“Recalc”](../usage/recalc.md)
* [“Frequency File Generator”](../usage/generators/frequency-file-generator.md)
* [“Readability Report Generator”](../usage/generators/readability-report-generator.md)

## Morph Stats & Graphs

In the "Shift"-click version of the Stats window, you can
see [stats ands graphs over your learned morphs](../usage/statistics.md).
