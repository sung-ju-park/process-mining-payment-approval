"""전체 분석 실행: python src/run_all.py"""
import json
import warnings

import pandas as pd

import conformance, discovery, drivers, figures, load, performance, report, rework, whatif
from config import OUT, PROCESSED

warnings.filterwarnings("ignore")


def main():
    if not (PROCESSED / "events.pkl").exists():
        load.main()
    ev = pd.read_pickle(PROCESSED / "events.pkl")
    cases = pd.read_pickle(PROCESSED / "cases.pkl")
    print("1/6 프로세스 발견"); disc = discovery.run(ev, cases)
    print("2/6 성능 분석"); perf, seg = performance.run(ev, cases)
    print("3/6 재작업 분석"); rw = rework.run(ev, cases)
    print("4/6 규정 준수"); conf = conformance.run(ev, cases)
    print("5/6 요인 분석"); dr = drivers.run(cases)
    print("6/6 시나리오"); wi = whatif.run(ev, cases, seg)
    res = {"overview": {"events": int(len(ev)), "cases": int(len(cases)),
                        "base_cases": int((cases["start"] >= pd.Timestamp("2018-01-01", tz="Europe/Amsterdam")).sum()),
                        "outcomes": cases["outcome"].value_counts().to_dict(),
                        "period": [str(ev["ts"].min().date()), str(ev["ts"].max().date())]},
           "discovery": disc, "performance": perf, "rework": rw, "conformance": conf, "drivers": dr, "whatif": wi}
    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    figures.all_figs(perf, dr, wi)
    report.build(res)
    print("완료:", OUT / "report.html")


if __name__ == "__main__":
    main()
