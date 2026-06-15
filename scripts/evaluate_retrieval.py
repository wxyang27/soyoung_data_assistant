import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app
from app.services.retrieval import search_knowledge


DEFAULT_EVAL_FILE = PROJECT_ROOT / "knowledge" / "eval" / "eval_questions.yaml"


def parse_eval_questions(path: Path) -> list[dict]:
    cases = []
    current = None
    current_list_name = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- question:"):
            if current:
                cases.append(current)
            current = {
                "question": stripped.removeprefix("- question:").strip().strip('"').strip("'"),
                "expected_keywords": [],
                "expected_topics": [],
            }
            current_list_name = None
            continue

        if current is None:
            continue

        if stripped in {"expected_keywords:", "expected_topics:"}:
            current_list_name = stripped.removesuffix(":")
            continue

        if stripped.startswith("- ") and current_list_name:
            current[current_list_name].append(stripped.removeprefix("- ").strip().strip('"').strip("'"))

    if current:
        cases.append(current)
    return cases


def normalize(text: str) -> str:
    return (text or "").lower().replace(" ", "")


def chunk_text(chunk: dict) -> str:
    return "\n".join(
        [
            chunk.get("title") or "",
            chunk.get("filename") or "",
            chunk.get("source_path") or "",
            chunk.get("topic") or "",
            chunk.get("snippet") or "",
            chunk.get("content") or "",
        ]
    )


def evaluate_case(case: dict, top_k: int, min_keyword_hits: int) -> dict:
    chunks = search_knowledge(case["question"], top_k=top_k, include_content=True)
    combined = normalize("\n".join(chunk_text(chunk) for chunk in chunks))
    topics = {chunk.get("topic") for chunk in chunks}

    keyword_hits = [
        keyword
        for keyword in case.get("expected_keywords", [])
        if normalize(keyword) in combined
    ]
    topic_hits = [
        topic
        for topic in case.get("expected_topics", [])
        if topic in topics
    ]

    passed = bool(chunks) and len(keyword_hits) >= min_keyword_hits
    return {
        "question": case["question"],
        "passed": passed,
        "keyword_hits": keyword_hits,
        "topic_hits": topic_hits,
        "chunks": chunks,
    }


def print_result(result: dict, top_k: int):
    mark = "PASS" if result["passed"] else "FAIL"
    print(f"\n[{mark}] {result['question']}")
    print(f"  keyword_hits: {', '.join(result['keyword_hits']) or '-'}")
    print(f"  topic_hits: {', '.join(result['topic_hits']) or '-'}")

    for index, chunk in enumerate(result["chunks"][:top_k], start=1):
        print(
            "  "
            f"#{index} score={chunk['score']} topic={chunk['topic']} "
            f"file={chunk['filename']} title={chunk['title']}"
        )
        print(f"     {chunk['snippet'][:120]}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate keyword retrieval over SQLite kb_chunks.")
    parser.add_argument("--eval-file", default=str(DEFAULT_EVAL_FILE))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--min-keyword-hits",
        type=int,
        default=1,
        help="A case passes if TopK contains at least this many expected keywords.",
    )
    args = parser.parse_args()

    eval_file = Path(args.eval_file)
    cases = parse_eval_questions(eval_file)
    if not cases:
        print(f"No evaluation cases found: {eval_file}")
        sys.exit(1)

    app = create_app()
    results = []
    with app.app_context():
        for case in cases:
            result = evaluate_case(case, top_k=args.top_k, min_keyword_hits=args.min_keyword_hits)
            results.append(result)
            print_result(result, top_k=args.top_k)

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    hit_rate = passed / total if total else 0
    print()
    print(f"Summary: passed={passed}/{total}, hit_rate={hit_rate:.0%}, top_k={args.top_k}")

    if passed != total:
        sys.exit(2)


if __name__ == "__main__":
    main()
