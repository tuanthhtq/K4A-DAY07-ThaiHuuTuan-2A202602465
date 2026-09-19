from __future__ import annotations

import argparse
import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path("data/university")


@dataclass(frozen=True)
class ContentRange:
    start: str
    stop: str | None = None
    start_occurrence: int = 1


CONTENT_RANGES = {
    "ktx-humg-noi-quy-quy-dinh.md": ContentRange("NỘI QUY KÝ TÚC XÁ", "Tải về tại đây"),
    "ktx-ktxhcm-tan-sinh-vien.md": ContentRange("Năm học 2026 – 2027", "Thiết kế bởi"),
    "ktx-noi-quy.md": ContentRange("NỘI QUI KÝ TÚC XÁ"),
    "ktx-quy-dinh-sinh-hoat-ung-xu.md": ContentRange(
        "QUI ĐỊNH VỀ SINH HOẠT, HỌC TẬP VÀ ỨNG XỬ"
    ),
    "ktx-tdtu-dang-ky-noi-tru.md": ContentRange(
        "I. Thời gian, địa điểm, đối tượng đăng ký",
        "Hướng dẫn",
    ),
    "ktx-vi-pham-khung-ky-luat.md": ContentRange(
        "NỘI DUNG VI PHẠM NỘI QUY KÝ TÚC XÁ VÀ KHUNG XỬ LÝ KỶ LUẬT",
        "Log in to post comments",
    ),
    "nha-cong-vu-can-bo.md": ContentRange("GIỚI THIỆU CHUNG", "Tin tức & Sự kiện"),
    "quy-che-hssv-noi-tru.md": ContentRange(
        "BỘ GIÁO DỤC VÀ ĐÀO TẠO",
        "Phụ lục số I",
        start_occurrence=2,
    ),
}


NOISE_LINES = {
    "Nhảy đến nội dung",
    "Đang theo dõi",
    "Log in to post comments",
    "Về đầu trang",
    "THEO DÕI CHÚNG TÔI TRÊN",
    "Xem tất cả",
    "x",
}

NOISE_PATTERNS = [
    re.compile(r"^Submitted by\b", re.IGNORECASE),
    re.compile(r"^on \d{1,2} [A-Za-z]+ \d{4}$", re.IGNORECASE),
    re.compile(r"^TDTU, \d{1,2}/\d{1,2}/\d{4}$", re.IGNORECASE),
    re.compile(r"^-?\s*Email: This email address is being protected", re.IGNORECASE),
    re.compile(r"^Design by\b", re.IGNORECASE),
    re.compile(r"^Thiết kế bởi\b", re.IGNORECASE),
]

STRUCTURAL_HEADING_PATTERNS = [
    re.compile(r"^(Điều\s+\d+[^\n]*)$", re.IGNORECASE),
    re.compile(r"^(Chương\s+[IVXLCDM\d]+[^\n]*)$", re.IGNORECASE),
    re.compile(r"^(ĐIỀU\s+[IVXLCDM]+\s*:[^\n]*)$"),
    re.compile(r"^([IVXLCDM]+\.\s*[^\n]+)$"),
    re.compile(r"^(\d+(?:\.\d+)+\.\s*[^\n]+)$"),
    re.compile(r"^(Bước\s+\d+[^\n]*)$", re.IGNORECASE),
]


def _normalize_line(line: str) -> str:
    normalized = unicodedata.normalize("NFC", line)
    normalized = normalized.replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"[ \t]+", " ", normalized).strip()


def _marker_value(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line).strip()


def _split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return [], lines
    return lines[: closing_index + 1], lines[closing_index + 1 :]


def _extract_content(filename: str, lines: list[str]) -> list[str]:
    title = next((line.strip() for line in lines if line.strip().startswith("# ")), None)
    content_range = CONTENT_RANGES.get(filename)
    if content_range is None:
        return lines

    normalized_lines = [_normalize_line(line) for line in lines]
    start_indexes = [
        index
        for index, line in enumerate(normalized_lines)
        if _marker_value(line).casefold() == content_range.start.casefold()
    ]
    heading_start_indexes = [index for index in start_indexes if normalized_lines[index].startswith("#")]
    occurrence_index = content_range.start_occurrence - 1
    if heading_start_indexes:
        start_index = heading_start_indexes[0]
    elif occurrence_index < len(start_indexes):
        start_index = start_indexes[occurrence_index]
    else:
        raise ValueError(f"Start marker not found in {filename}: {content_range.start}")

    stop_index = len(lines)
    if content_range.stop:
        stop_index = next(
            (
                index
                for index, line in enumerate(normalized_lines[start_index + 1 :], start=start_index + 1)
                if _marker_value(line).casefold() == content_range.stop.casefold()
            ),
            len(lines),
        )

    extracted = lines[start_index:stop_index]
    if title and _normalize_line(extracted[0]) != _normalize_line(title):
        return [title, "", *extracted]
    return extracted


def _is_noise(line: str) -> bool:
    if line in NOISE_LINES:
        return True
    if line and set(line) <= {"-", "_", "="}:
        return True
    return any(pattern.search(line) for pattern in NOISE_PATTERNS)


def _as_heading(line: str) -> str:
    if line.startswith("#"):
        return line
    for pattern in STRUCTURAL_HEADING_PATTERNS:
        if pattern.match(line):
            return f"## {line}"
    if 5 <= len(line) <= 120 and " " in line and any(character.isalpha() for character in line):
        letters = [character for character in line if character.isalpha()]
        if letters and all(character.isupper() for character in letters):
            return f"## {line}"
    return line


def clean_text(path: Path) -> str:
    original = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(original)
    body = _extract_content(path.name, body)

    cleaned_lines: list[str] = []
    previous_content = ""
    for raw_line in body:
        line = _normalize_line(raw_line)
        if _is_noise(line):
            continue
        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            continue

        line = _as_heading(line)
        comparable = line.casefold()
        if comparable == previous_content:
            continue
        cleaned_lines.append(line)
        previous_content = comparable

    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()

    normalized_frontmatter = [_normalize_line(line) for line in frontmatter]
    output_lines = [*normalized_frontmatter, "", *cleaned_lines]
    return "\n".join(output_lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean the university Markdown corpus.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--apply", action="store_true", help="Write cleaned content to the corpus files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = sorted(args.data_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"No Markdown files found in {args.data_dir}")

    cleaned_by_path = {path: clean_text(path) for path in paths}
    for path, cleaned in cleaned_by_path.items():
        original = path.read_text(encoding="utf-8")
        removed = len(original) - len(cleaned)
        print(
            f"{path.name}: chars {len(original)} -> {len(cleaned)} "
            f"({removed} removed), lines {len(original.splitlines())} -> {len(cleaned.splitlines())}"
        )

    if not args.apply:
        print("Dry run only. Re-run with --apply to update the corpus.")
        return 0

    backup_dir = Path(tempfile.mkdtemp(prefix="lab07-university-corpus-"))
    for path in paths:
        shutil.copy2(path, backup_dir / path.name)
        path.write_text(cleaned_by_path[path], encoding="utf-8", newline="\n")
    print(f"Backup created at: {backup_dir}")
    print(f"Updated {len(paths)} corpus files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
