"""Run ask() on eval/eval.json and print a score table.
A case passes only if status matches, every expected citation is returned,
and every must_contain string appears in the answer."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ask import ask  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
cases = json.loads((Path(__file__).parent / "eval.json").read_text(encoding="utf-8"))

rows, passed = [], 0
for c in cases:
    r = ask(c["question"], c["as_of"])
    got = {x["clause"] for x in r["citations"]}
    s_ok = r["status"] == c["expected_status"]
    c_ok = set(c["expected_citations"]) <= got
    a_ok = all(t in r["answer"] for t in c["must_contain"])
    ok = s_ok and c_ok and a_ok
    passed += ok
    rows.append((c["id"], "Y" if c.get("adversarial") else "", r["status"],
                 "ok" if s_ok else "X", "ok" if c_ok else "X", "ok" if a_ok else "X", "PASS" if ok else "FAIL"))
    if not ok:
        print(f"[{c['id']}] expected {c['expected_status']} {c['expected_citations']} {c['must_contain']}\n"
              f"   got {r['status']} {sorted(got)}\n   {r['answer']}\n")

hdr = ("id", "adv", "status returned", "status", "cites", "answer", "result")
w = [max(len(str(x[i])) for x in rows + [hdr]) for i in range(len(hdr))]
line = lambda x: "  ".join(str(v).ljust(w[i]) for i, v in enumerate(x))
print(line(hdr)); print("-" * (sum(w) + 2 * len(w)))
for r in rows:
    print(line(r))
adv = [r for r in rows if r[1]]
print(f"\nTotal: {passed}/{len(rows)}  |  adversarial: {sum(r[-1] == 'PASS' for r in adv)}/{len(adv)}")
sys.exit(0 if passed == len(rows) else 1)
