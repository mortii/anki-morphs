from __future__ import annotations

import os
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import anki
from aqt import mw


def extract_ass_text(file_path: Path) -> list[str]:
    """
    Anatomy of ass files:
    - the lines that have the actual subtitles always start with a "Dialogue:" and the
        text starts after the ninth comma.
    """
    dialogue_lines = []

    with open(file_path, encoding="utf-8") as file:
        for line in file:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) > 9:  # Ensure there is subtitle text present
                    dialogue_lines.append(parts[9].strip())

    return dialogue_lines


def extract_srt_text(file_path: Path) -> list[str]:
    """
    Anatomy of srt files:
    - line is digit: the subtitle segment identifier
    - line contains "-->": timing of the subtitle segment
    - blank lines: indicates that the current subtitle segment is complete and previous
        lines should be combined
    """
    subtitle_texts: list[str] = []
    current_segment_text: list[str] = []

    with open(file_path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()  # to prevent irregularities

            if line.isdigit() or "-->" in line:
                continue

            if not line:
                if current_segment_text:
                    subtitle_texts.append(" ".join(current_segment_text))
                    current_segment_text = []
            else:
                current_segment_text.append(line)

    return subtitle_texts


def extract_vtt_text(file_path: Path) -> list[str]:
    subtitle_texts = []

    with open(file_path, encoding="utf-8") as file:
        file.readline()  # skips the "WEBVTT" header

        for line in file:
            line = line.strip()
            if "-->" not in line and line:
                subtitle_texts.append(line)

    return subtitle_texts


def extract_epub_text(epub_path: Path) -> list[str]:
    assert mw is not None

    # Use a generator to yield text lines for better memory efficiency
    def extract_text(_temp_dir: str) -> Iterator[list[str]]:
        for _root, _, _files in os.walk(_temp_dir):
            for file in filter(lambda f: f.endswith((".xhtml", ".html")), _files):
                file_path = Path(_root, file)
                yield extract_html_text(file_path)

    # Create an auto-cleaning temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(epub_path) as epub:
            epub.extractall(temp_dir)
            text_content: list[str] = []

            for batch in extract_text(temp_dir):
                text_content.extend(batch)

            return text_content


def extract_html_text(file_path: Path) -> list[str]:
    """
    Returns a list to make it consistent with the other extractors
    """
    with open(file_path, encoding="utf-8") as file:
        content = file.read()
    content = anki.utils.strip_html(content)
    return [content]


def extract_basic_text(file_path: Path) -> list[str]:
    with open(file_path, encoding="utf-8") as file:
        return [line.strip() for line in file]
