"""원본 XES 로그를 읽어 분석용 이벤트 테이블과 케이스 테이블을 만든다."""
import warnings

import numpy as np
import pandas as pd

from config import PROCESSED, RAW, short

warnings.filterwarnings("ignore")


def load_events(path=RAW) -> pd.DataFrame:
    import pm4py
    raw = pm4py.read_xes(str(path))
    ev = pd.DataFrame({
        "case_id": raw["case:concept:name"],
        "event_id": raw["id"],
        "activity": raw["concept:name"].map(short),
        "ts": pd.to_datetime(raw["time:timestamp"], utc=True).dt.tz_convert("Europe/Amsterdam"),
        "role": raw["org:role"],
        "resource": raw["org:resource"],
        "org": raw["case:OrganizationalEntity"],
        "project": raw["case:Project"],
        "amount": raw["case:RequestedAmount"].astype(float),
    })
    # 같은 시각 이벤트의 순서는 원본 이벤트 id 순서를 따른다
    ev["_seq"] = ev["event_id"].str.extract(r"_(\d+)$").astype(float)
    ev = ev.sort_values(["case_id", "ts", "_seq"]).drop(columns="_seq").reset_index(drop=True)
    ev["step"] = ev.groupby("case_id").cumcount()
    return ev


def outcome(acts: list) -> str:
    if "Payment Handled" in acts:
        return "지급 완료"
    if acts == ["SAVED / EMPLOYEE"]:
        return "임시저장만"
    if acts[-1].startswith("REJECTED"):
        return "반려 종료"
    return "진행 중"


def build_cases(ev: pd.DataFrame) -> pd.DataFrame:
    g = ev.groupby("case_id")
    acts = g["activity"].apply(list)
    start, end = g["ts"].min(), g["ts"].max()
    c = pd.DataFrame({
        "start": start, "end": end,
        "duration_d": (end - start).dt.total_seconds() / 86400,
        "n_events": g.size(),
        "org": g["org"].first(), "project": g["project"].first(), "amount": g["amount"].first(),
        "outcome": acts.map(outcome),
        "variant": acts.map(lambda a: " → ".join(a)),
        "n_reject": acts.map(lambda a: sum(x.startswith("REJECTED") and x != "REJECTED / EMPLOYEE" for x in a)),
        "n_submit": acts.map(lambda a: a.count("SUBMITTED / EMPLOYEE")),
        "has_admin": acts.map(lambda a: "APPROVED / ADMINISTRATION" in a),
        "has_budget": acts.map(lambda a: "APPROVED / BUDGET OWNER" in a),
        "has_pre": acts.map(lambda a: "APPROVED / PRE_APPROVER" in a),
    })
    c["rework"] = c["n_reject"] > 0
    c["year"] = c["start"].dt.year
    c["quarter"] = c["start"].dt.to_period("Q").astype(str)
    c["submit_wd"] = c["start"].dt.dayofweek  # 0=월
    c["log_amount"] = np.log1p(c["amount"].clip(lower=0))
    return c


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ev = load_events()
    cases = build_cases(ev)
    ev.to_pickle(PROCESSED / "events.pkl")
    cases.to_pickle(PROCESSED / "cases.pkl")
    print(f"이벤트 {len(ev):,}개, 케이스 {len(cases):,}건, 활동 {ev.activity.nunique()}종")
    print(cases["outcome"].value_counts().to_string())


if __name__ == "__main__":
    main()
