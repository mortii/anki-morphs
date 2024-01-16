# Changes To Anki

After installing AnkiMorphs you will find that some changes have been made to Anki.

## Toolbar

![toolbar.png](../../img/toolbar.png)

The toolbar now has three new items:
- [Recalc](../usage/recalc.md)
- “U”, which stands for Known Unique Morphs
- "A", which stands for All Known Morphs

For languages that don't have inflections (Chinese, etc.), U and A will always have the same number, 


<details>
  <summary style="display:list-item">English examples of U and A</summary>


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
    <td>go</td>
    <td>break</td>
    <td>read</td>
    <td>walk</td>
</tr>
<tr>
    <td>went</td>
    <td>broke</td>
    <td>read</td>
    <td>walked</td>
</tr>
<tr>
    <td>going</td>
    <td class="morph-variation-selected_cell">breaking</td>
    <td>reading</td>
    <td>walking</td>
</tr>
<tr>
    <td>gone</td>
    <td>broken</td>
    <td>read</td>
    <td>walked</td>
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
    <td>go</td>
    <td class="morph-variation-selected_cell">break</td>
    <td>read</td>
    <td>walk</td>
</tr>
<tr>
    <td>went</td>
    <td>broke</td>
    <td>read</td>
    <td>walked</td>
</tr>
<tr>
    <td>going</td>
    <td class="morph-variation-selected_cell">breaking</td>
    <td>reading</td>
    <td>walking</td>
</tr>
<tr>
    <td>gone</td>
    <td>broken</td>
    <td>read</td>
    <td>walked</td>
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
    <td>go</td>
    <td class="morph-variation-selected_cell">break</td>
    <td>read</td>
    <td>walk</td>
</tr>
<tr>
    <td>went</td>
    <td>broke</td>
    <td>read</td>
    <td class="morph-variation-selected_cell">walked</td>
</tr>
<tr>
    <td>going</td>
    <td class="morph-variation-selected_cell">breaking</td>
    <td>reading</td>
    <td>walking</td>
</tr>
<tr>
    <td>gone</td>
    <td>broken</td>
    <td>read</td>
    <td>walked</td>
</tr>
</table>
</div>

<br>
</blockquote>
</details>


<details>
  <summary style="display:list-item">Japanese examples of U and A</summary>


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

An AnkiMorphs menu is added to "Tools" menu and has the options:

* [“Settings”](../setup/settings.md)
* [“Recalc”](../usage/recalc.md)
* [“Frequency File Generator”](../usage/generators/frequency-file-generator.md)
* [“Readability Report Generator”](../usage/generators/readability-report-generator.md)
* [“Known Morphs Exporter”](../usage/known-morphs-exporter.md)
