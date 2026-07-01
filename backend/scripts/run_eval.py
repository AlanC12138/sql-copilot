"""Runs the NL->SQL benchmark against the live agent and scores it two ways:

- execution-match: do the result rows match the gold query's rows (order-independent,
  numeric values rounded to 2dp)? This is the headline number — it doesn't care how the
  SQL is phrased, only whether the answer is right.
- exact-match: does the generated SQL text match the gold SQL after whitespace/case
  normalization? Reported as a secondary, much stricter signal — there are many correct
  ways to phrase the same query, so a low exact-match rate alongside a high
  execution-match rate is expected, not a problem.
"""
import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.loop import run_agent
from app.db.demo_engine import get_demo_engine

BENCHMARK_PATH = Path(__file__).resolve().parents[1] / "eval" / "benchmark.json"
REPORT_PATH = Path(__file__).resolve().parents[1] / "eval" / "results.json"


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().rstrip(";")).lower()


def normalize_cell(value):
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 2)
    if value is None:
        return None
    return str(value).strip().lower()


def normalize_rows(rows):
    return sorted(tuple(normalize_cell(v) for v in row) for row in rows)


def run_gold(engine, sql: str) -> list[list]:
    with engine.connect() as conn:
        result = conn.exec_driver_sql(sql)
        return [list(row) for row in result.fetchall()]


def evaluate_question(item: dict) -> dict:
    engine = get_demo_engine()
    gold_rows = run_gold(engine, item["sql"])
    agent_result = run_agent(item["question"])

    record = {
        "id": item["id"],
        "question": item["question"],
        "gold_sql": item["sql"],
        "agent_sql": agent_result.sql,
        "agent_answer": agent_result.answer,
        "agent_failed": agent_result.failed,
        "exact_match": False,
        "execution_match": False,
    }

    if agent_result.sql:
        record["exact_match"] = normalize_sql(agent_result.sql) == normalize_sql(item["sql"])

    if agent_result.rows is not None:
        try:
            record["execution_match"] = normalize_rows(agent_result.rows) == normalize_rows(gold_rows)
        except TypeError as exc:
            # The agent can select columns we didn't anticipate (e.g. a nullable column
            # mixed with non-null values in the same result set), which can make the rows
            # unsortable. Score it as a miss rather than crashing the whole benchmark run.
            record["comparison_error"] = str(exc)

    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions")
    args = parser.parse_args()

    benchmark = json.loads(BENCHMARK_PATH.read_text())
    if args.limit:
        benchmark = benchmark[: args.limit]

    results = []
    for item in benchmark:
        record = evaluate_question(item)
        results.append(record)
        mark = "PASS" if record["execution_match"] else "FAIL"
        print(f"[{mark}] #{record['id']:>2} {record['question']}")
        if not record["execution_match"]:
            print(f"       gold:  {record['gold_sql']}")
            print(f"       agent: {record['agent_sql']}")

    total = len(results)
    executed = sum(r["execution_match"] for r in results)
    exact = sum(r["exact_match"] for r in results)

    print()
    print(f"Execution-match accuracy: {executed}/{total} ({100 * executed / total:.1f}%)")
    print(f"Exact-match accuracy:     {exact}/{total} ({100 * exact / total:.1f}%)  (strict, phrasing-sensitive)")

    REPORT_PATH.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nFull report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
