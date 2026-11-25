"""Run LexAI, NoRAG and SimpleRAG on the benchmark and save every answer.

Unlike the original runner, an API failure is never saved as an answer: a
failed query is retried with growing waits, and if it still fails the run
stops so it can be resumed later. Answers are saved one per line as they
arrive, so a stopped run picks up where it left off.

Run from backend/ with the backend virtualenv:

    python scripts/rerun_eval.py --out evaluation/results_rerun --limit 10
    python scripts/rerun_eval.py --out evaluation/results_rerun

API keys are read from the environment, or from --env-file (a .env with
GROQ_API_KEY, GROQ_API_KEY_2, ...). Nothing in that file is printed.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

SYSTEMS = ("LexAI", "NoRAG", "SimpleRAG")
# SmartRetriever attributes each ablation sets on LexAI's retriever.
LEXAI_VARIANTS = {
    "full": {},
    "no_replacement_fetch": {"use_transition_expansion": False},
    "no_transition_middleware": {"use_bns_middleware": False},
}
RETRY_WAITS_S = (20, 40, 80, 160, 300)
ERROR_ANSWER = re.compile(r"^\s*(error\b|\[placeholder)", re.I)


def is_error_response(response):
    """True when a response records a failed call instead of an answer.

    An empty answer counts as failed: a reasoning model that spends its whole
    output budget on reasoning returns no text.
    """
    if response.get("error") or str(response.get("confidence", "")).upper() == "ERROR":
        return True
    if not str(response.get("answer") or "").strip():
        return True
    return bool(ERROR_ANSWER.match(str(response.get("answer", ""))))


def load_done(path):
    """Query ids already answered in a checkpoint file."""
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["query_id"]] = rec
    return done


def answer_with_retry(call, query_id, system):
    """Call a system until it returns a real answer; None if it never does."""
    for attempt, wait in enumerate((0,) + RETRY_WAITS_S):
        if wait:
            print(f"    {system} {query_id}: API error, retry {attempt} in {wait}s", flush=True)
            time.sleep(wait)
        response = call()
        if not is_error_response(response):
            return response
        last = str(response.get("error") or response.get("answer", ""))[:160]
    print(f"    {system} {query_id}: still failing after {len(RETRY_WAITS_S)} retries: {last}", flush=True)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ground-truth", default="evaluation/ground_truth_lexeval_key_393.xlsx")
    ap.add_argument("--index", default=str(BACKEND / "legal_research_db_clean"))
    ap.add_argument("--env-file", type=Path, default=None)
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS), choices=SYSTEMS)
    ap.add_argument("--query-ids", nargs="+", default=None, help="run only these query ids")
    ap.add_argument("--limit", type=int, default=None, help="run only the first N queries")
    ap.add_argument("--eval-regime", choices=["forced-answer", "abstain-allowed"], default="forced-answer")
    ap.add_argument("--categories", nargs="+", default=None, help="run only these benchmark categories")
    ap.add_argument("--lexai-variant", choices=sorted(LEXAI_VARIANTS), default="full",
                    help="ablation: switch off part of LexAI's transition handling")
    args = ap.parse_args()

    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    os.environ["LEXAI_CHROMA_PATH"] = str(Path(args.index).resolve())
    os.chdir(BACKEND)

    from evaluation.run_evaluation import EvaluationRunner

    args.out.mkdir(parents=True, exist_ok=True)
    runner = EvaluationRunner(args.ground_truth, str(args.out), eval_regime=args.eval_regime)
    gt = runner.load_ground_truth()
    rows = gt.to_dict("records")
    if args.query_ids:
        wanted = {q for arg in args.query_ids for q in arg.split()}
        unknown = wanted - {r["query_id"] for r in rows}
        if unknown:
            raise SystemExit(f"unknown query ids: {sorted(unknown)}")
        rows = [r for r in rows if r["query_id"] in wanted]
    if args.categories:
        unknown = set(args.categories) - {r["category"] for r in rows}
        if unknown:
            raise SystemExit(f"unknown categories: {sorted(unknown)}")
        rows = [r for r in rows if r["category"] in set(args.categories)]
    if args.limit:
        rows = rows[:args.limit]
    for attr, value in LEXAI_VARIANTS[args.lexai_variant].items():
        if runner.lexai is None or not hasattr(runner.lexai.retriever, attr):
            raise SystemExit(f"cannot apply variant {args.lexai_variant}: retriever has no {attr}")
        setattr(runner.lexai.retriever, attr, value)
    eval_mode = args.eval_regime == "forced-answer"

    baselines = None
    if {"NoRAG", "SimpleRAG"} & set(args.systems):
        from evaluation.baselines import BaselineRunner
        baselines = BaselineRunner()

    calls = {
        "LexAI": lambda q: runner.run_lexai([q], eval_mode=eval_mode)[0],
        "NoRAG": lambda q: baselines.run_no_rag(q, eval_mode=eval_mode),
        "SimpleRAG": lambda q: baselines.run_simple_rag(q, eval_mode=eval_mode),
    }
    meta = {"ground_truth": args.ground_truth, "index": os.environ["LEXAI_CHROMA_PATH"],
            "eval_regime": args.eval_regime, "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "max_tokens": os.getenv("GROQ_MAX_TOKENS", "2048"), "lexai_variant": args.lexai_variant,
            "categories": args.categories,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (args.out / "run_config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    for system in args.systems:
        path = args.out / f"{system.lower()}_responses.jsonl"
        done = load_done(path)
        todo = [r for r in rows if r["query_id"] not in done]
        print(f"\n{system}: {len(done)} already saved, {len(todo)} to run", flush=True)
        with path.open("a", encoding="utf-8") as fh:
            for n, row in enumerate(todo, 1):
                response = answer_with_retry(lambda: calls[system](row["query"]), row["query_id"], system)
                if response is None:
                    raise SystemExit(f"{system} stopped at {row['query_id']}; rerun the same command to resume")
                response.update(query_id=row["query_id"], query=row["query"], system=system)
                fh.write(json.dumps(response, ensure_ascii=False, default=str) + "\n")
                fh.flush()
                print(f"  {system} {n}/{len(todo)} {row['query_id']}", flush=True)
    print("\nall requested systems complete:", args.out)


if __name__ == "__main__":
    main()
