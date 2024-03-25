import importlib
import importlib.util
import sys
from types import ModuleType
from typing import Optional

posseg: Optional[ModuleType] = None

successful_startup: bool = False

################################################################################
# This section about cjk_ideographs is from zhon/hanzi.py
# zhon: https://github.com/tsroten/zhon
################################################################################

#: Character code ranges for pertinent CJK ideograph Unicode blocks.
# cjk_ideographs = (
CJK_IDEOGRAPHS: str = (
    "\u3007"  # Ideographic number zero, see issue #17
    "\u4E00-\u9FFF"  # CJK Unified Ideographs
    "\u3400-\u4DBF"  # CJK Unified Ideographs Extension A
    "\uF900-\uFAFF"  # CJK Compatibility Ideographs
)
if sys.maxunicode > 0xFFFF:
    CJK_IDEOGRAPHS += (
        "\U00020000-\U0002A6DF"  # CJK Unified Ideographs Extension B
        "\U0002A700-\U0002B73F"  # CJK Unified Ideographs Extension C
        "\U0002B740-\U0002B81F"  # CJK Unified Ideographs Extension D
        "\U0002F800-\U0002FA1F"  # CJK Compatibility Ideographs Supplement
    )
################################################################################


def import_jieba() -> None:
    global posseg, successful_startup

    if importlib.util.find_spec("1857311956"):
        posseg = importlib.import_module("1857311956.jieba.posseg")
    elif importlib.util.find_spec("ankimorphs_chinese_jieba"):
        posseg = importlib.import_module("ankimorphs_chinese_jieba.jieba.posseg")
    else:
        return

    successful_startup = True
