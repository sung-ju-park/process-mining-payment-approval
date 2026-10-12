"""성능 분석: 시간이 어디서 새는가, 지급 배치 구조, 처리 기간 추세."""
import pandas as pd

from config import BASE_FROM, ko
from discovery import transitions


def segments(ev: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    """지급 완료 건을 결재 / 지급요청 대기 / 지급 대기 세 구간으로 나눈다."""
    paid = cases.index[cases["outcome"] == "지급 완료"]
    e = ev[ev["case_id"].isin(paid)]
    last = lambda a: e[e["activity"] == a].groupby("case_id")["ts"].max()
    s = pd.concat({"first": e.groupby("case_id")["ts"].min(), "final": last("FINAL_APPROVED / SUPERVISOR"),
                   "req": last("Request Payment"), "paid": last("Payment Handled")}, axis=1).dropna()
    d = lambda a, b: (s[b] - s[a]).dt.total_seconds() / 86400
    s["결재"], s["지급요청 대기"], s["지급 대기"] = d("first", "final"), d("final", "req"), d("req", "paid")
    s = s[(s[["결재", "지급요청 대기", "지급 대기"]] >= 0).all(axis=1)]
    return s.join(cases[["quarter", "year", "has_budget", "rework", "org"]])


def run(ev, cases):
    t0 = pd.Timestamp(BASE_FROM, tz="Europe/Amsterdam")
    base = cases[cases["start"] >= t0]
    bev = ev[ev["case_id"].isin(base.index)]
    tr = transitions(bev).sort_values("total", ascending=False)
    tr["from_ko"], tr["to_ko"] = tr["activity"].map(ko), tr["next"].map(ko)
    seg = segments(ev, cases)
    seg_b = seg[seg["first"] >= t0]

    ph = bev[bev["activity"] == "Payment Handled"]["ts"]
    rq = bev[bev["activity"] == "Request Payment"]["ts"]
    wd = ["월", "화", "수", "목", "금", "토", "일"]
    paid = base[base["outcome"] == "지급 완료"]

    # 같은 조직끼리 2017 vs 2018 비교 (구성 효과 제거)
    seg_all = seg.copy()
    orgs17 = set(cases[cases["year"] == 2017]["org"])
    same = seg_all[seg_all["org"].isin(orgs17)]

    out = {
        "paid_median": float(paid["duration_d"].median()), "paid_mean": float(paid["duration_d"].mean()),
        "paid_p90": float(paid["duration_d"].quantile(0.9)),
        "within7_pct": float((paid["duration_d"] <= 7).mean()),
        "top_transitions": tr.head(8)[["from_ko", "to_ko", "cases", "median", "p90", "share_of_wait"]].to_dict("records"),
        "post_approval_wait_share": float(tr[tr["activity"].isin(["FINAL_APPROVED / SUPERVISOR", "Request Payment"])
                                            & tr["next"].isin(["Request Payment", "Payment Handled"])]["share_of_wait"].sum()),
        "segment_median": seg_b[["결재", "지급요청 대기", "지급 대기"]].median().round(2).to_dict(),
        "segment_mean": seg_b[["결재", "지급요청 대기", "지급 대기"]].mean().round(2).to_dict(),
        "payment_weekday": {wd[k]: int(v) for k, v in ph.dt.dayofweek.value_counts().sort_index().items()},
        "payment_hour": {int(k): int(v) for k, v in ph.dt.hour.value_counts().sort_index().items()},
        "request_weekday": {wd[k]: int(v) for k, v in rq.dt.dayofweek.value_counts().sort_index().items()},
        "payment_batch_share": float(ph.dt.dayofweek.isin([0, 3]).mean()),
        "submit_weekday_median": {wd[k]: float(v) for k, v in
                                  paid[~paid["rework"]].groupby("submit_wd")["duration_d"].median().items()},
        "quarterly": seg.groupby("quarter")[["결재", "지급요청 대기", "지급 대기"]].median().round(2)
                        .join(cases.groupby("quarter").agg(건수=("duration_d", "size"),
                                                           예산책임자경유=("has_budget", "mean"))).reset_index().to_dict("records"),
        "same_orgs_by_year": same.groupby("year")[["결재", "지급요청 대기", "지급 대기"]].median().round(2).to_dict("index"),
        "budget_effect": seg_b.groupby("has_budget")[["결재", "지급요청 대기", "지급 대기"]].median().round(2).to_dict("index"),
        "budget_share": float(base["has_budget"].mean()),
    }
    seg.to_pickle(cases.attrs.get("processed", "") or "/dev/null") if False else None
    return out, seg_b
