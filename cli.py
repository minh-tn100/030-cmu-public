"""python cli.py review [--design claims.json] [--standards corpus.json] [--llm stub|claude] [--max-calls 60] [--out out]"""
import argparse, sys
from agent.pipeline import review
from agent.gateway import MissingKey

def main(argv=None):
    ap = argparse.ArgumentParser(prog="designbench"); sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review")
    r.add_argument("--design"); r.add_argument("--standards"); r.add_argument("--llm", choices=["stub", "claude"], default="stub")
    r.add_argument("--max-calls", type=int, default=100); r.add_argument("--max-tokens", type=int, default=200_000)
    r.add_argument("--max-gaps", type=int, default=3); r.add_argument("--compare", action="store_true", help="also run a one-call no-ToT baseline")
    r.add_argument("--seed", default="0"); r.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    try:
        rep = review(a.llm, a.out, a.design, a.standards, a.max_calls, a.max_tokens, a.max_gaps, compare=a.compare, seed=a.seed)
    except MissingKey as e:
        print(f"error: {e}", file=sys.stderr); return 3
    rv = rep["review"]
    print(f"{a.out}/report.html written: {rv['gap']} gap, {rv['ok']} ok, {rv['not_assessed']} not assessed; calls {rep['usage']['calls']}/{rep['usage']['max_calls']}")
    return 2 if rep["errors"] else 0

if __name__ == "__main__":
    sys.exit(main())
