from __future__ import annotations

import argparse
import io
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from dotenv import load_dotenv

from src import (
    EMBEDDING_PROVIDER_ENV,
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    HeadingChunker,
    LocalEmbedder,
    RecursiveChunker,
    SentenceChunker,
    _mock_embed,
)


DATA_DIR = Path("data/university")
DEFAULT_CHUNK_SIZE = 800
DEFAULT_TOP_K = 3


@dataclass(frozen=True)
class BenchmarkQuery:
    question: str
    gold_answer: str
    gold_doc_ids: tuple[str, ...]
    answer_terms: tuple[str, ...]
    metadata_filter: dict[str, str] | None = None


BENCHMARK_QUERIES = [
    BenchmarkQuery(
        question="Ký túc xá mở cửa và đóng cửa lúc mấy giờ?",
        gold_answer="Giờ mở cửa là 05:00 và giờ đóng cửa là 22:00.",
        gold_doc_ids=("ktx-quy-dinh-sinh-hoat-ung-xu", "ktx-noi-quy"),
        answer_terms=("05:00", "22:00"),
    ),
    BenchmarkQuery(
        question="Sinh viên đang bị kỷ luật từ mức nào thì không được đăng ký ở Ký túc xá TDTU?",
        gold_answer="Sinh viên đang thi hành kỷ luật cấp trường từ mức khiển trách trở lên không được đăng ký.",
        gold_doc_ids=("ktx-tdtu-dang-ky-noi-tru",),
        answer_terms=("khiển trách", "không được đăng ký"),
    ),
    BenchmarkQuery(
        question="Sinh viên vắng mặt tại khu nội trú quá bao lâu thì phải báo Ban quản lý?",
        gold_answer="Nếu vắng mặt quá 1 ngày, sinh viên phải báo với Ban quản lý khu nội trú.",
        gold_doc_ids=("quy-che-hssv-noi-tru",),
        answer_terms=("quá 1 ngày", "báo với Ban quản lý"),
    ),
    BenchmarkQuery(
        question="Hồ sơ đăng ký nội trú TDTU cần những giấy tờ cơ bản nào?",
        gold_answer=(
            "Hồ sơ gồm phiếu đăng ký ở nội trú, bản sao Căn cước công dân/Căn cước, "
            "giấy tờ minh chứng diện ưu tiên nếu có và giấy xác nhận cư trú khi cần."
        ),
        gold_doc_ids=("ktx-tdtu-dang-ky-noi-tru",),
        answer_terms=("Phiếu đăng ký", "Căn cước"),
    ),
    BenchmarkQuery(
        question="Những đối tượng nào được ưu tiên xét chỗ ở?",
        gold_answer=(
            "Đối với sinh viên, các nhóm ưu tiên gồm diện chính sách, người khuyết tật, "
            "mồ côi, sinh viên thuộc hộ nghèo hoặc vùng có điều kiện khó khăn."
        ),
        gold_doc_ids=(
            "ktx-tdtu-dang-ky-noi-tru",
            "quy-che-hssv-noi-tru",
        ),
        answer_terms=("khuyết tật", "mồ côi"),
        metadata_filter={"audience": "student"},
    ),
]


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return {}, text.strip()

    metadata: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, "\n".join(lines[closing_index + 1 :]).strip()


def build_chunker(strategy: str, chunk_size: int):
    if strategy == "fixed":
        return FixedSizeChunker(chunk_size=chunk_size, overlap=min(100, chunk_size // 5))
    if strategy == "sentence":
        return SentenceChunker(max_sentences_per_chunk=5)
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=chunk_size)
    if strategy == "heading":
        return HeadingChunker(chunk_size=chunk_size)
    raise ValueError(f"Unsupported chunking strategy: {strategy}")


def load_chunked_documents(data_dir: Path, strategy: str, chunk_size: int) -> tuple[list[Document], int]:
    chunker = build_chunker(strategy, chunk_size)
    documents: list[Document] = []
    source_count = 0

    for path in sorted(data_dir.glob("*.md")):
        metadata, content = parse_frontmatter(path)
        if not content:
            continue
        source_count += 1
        for index, chunk in enumerate(chunker.chunk(content)):
            chunk_metadata = {
                **metadata,
                "doc_id": path.stem,
                "chunk_index": index,
                "chunking_strategy": strategy,
            }
            documents.append(Document(id=f"{path.stem}#{index}", content=chunk, metadata=chunk_metadata))

    return documents, source_count


def create_embedder(provider: str):
    if provider == "local":
        return LocalEmbedder()
    if provider == "mock":
        return _mock_embed
    raise ValueError("Benchmark provider must be 'local' or 'mock'.")


def _contains_answer(content: str, terms: tuple[str, ...]) -> bool:
    normalized_content = unicodedata.normalize("NFC", content).casefold()
    return all(unicodedata.normalize("NFC", term).casefold() in normalized_content for term in terms)


def _score_results(query: BenchmarkQuery, results: list[dict]) -> int:
    for index, result in enumerate(results):
        doc_id = result["metadata"].get("doc_id")
        if doc_id in query.gold_doc_ids and _contains_answer(result["content"], query.answer_terms):
            return 2 if index == 0 else 1
    return 0


def _print_results(results: list[dict], output: TextIO) -> None:
    if not results:
        print("  No results", file=output)
        return

    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]
        preview = " ".join(result["content"].split())[:220]
        print(
            f"  {rank}. score={result['score']:.4f} "
            f"doc_id={metadata.get('doc_id')} chunk={metadata.get('chunk_index')}",
            file=output,
        )
        print(f"     {preview}", file=output)


def run_benchmark(
    data_dir: Path,
    strategy: str,
    chunk_size: int,
    provider: str,
) -> str:
    embedder = create_embedder(provider)
    documents, source_count = load_chunked_documents(data_dir, strategy, chunk_size)
    store = EmbeddingStore(collection_name=f"benchmark_{strategy}", embedding_fn=embedder)
    store.add_documents(documents)

    output = io.StringIO()
    print("=== LAB 07 RETRIEVAL BENCHMARK ===", file=output)
    print(f"Data directory: {data_dir}", file=output)
    print(f"Embedding backend: {getattr(embedder, '_backend_name', provider)}", file=output)
    print(f"Chunking strategy: {strategy}", file=output)
    print(f"Chunk size: {chunk_size}", file=output)
    print(f"Source documents: {source_count}", file=output)
    print(f"Stored chunks: {store.get_collection_size()}", file=output)

    total_score = 0
    for index, query in enumerate(BENCHMARK_QUERIES, start=1):
        print(f"\n--- QUERY {index} ---", file=output)
        print(f"Question: {query.question}", file=output)
        print(f"Gold answer: {query.gold_answer}", file=output)
        print(f"Metadata filter: {query.metadata_filter}", file=output)
        results = store.search_with_filter(
            query.question,
            top_k=DEFAULT_TOP_K,
            metadata_filter=query.metadata_filter,
        )
        _print_results(results, output)
        query_score = _score_results(query, results)
        total_score += query_score
        print(f"Retrieval score: {query_score}/2", file=output)

        if query.metadata_filter:
            print("  A/B without metadata filter:", file=output)
            _print_results(store.search(query.question, top_k=DEFAULT_TOP_K), output)

    print(f"\nTOTAL RETRIEVAL SCORE: {total_score}/10", file=output)
    return output.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lab 07 retrieval benchmark.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument(
        "--strategy",
        choices=("fixed", "sentence", "recursive", "heading"),
        default="heading",
    )
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument(
        "--provider",
        choices=("local", "mock"),
        default=None,
        help="Defaults to EMBEDDING_PROVIDER or local when unset.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    load_dotenv(override=False)
    args = parse_args()
    provider = args.provider or os.getenv(EMBEDDING_PROVIDER_ENV, "local").strip().lower()
    result = run_benchmark(args.data_dir, args.strategy, args.chunk_size, provider)
    print(result, end="")
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
