"""재작업(반려 후 재제출) 분석: 얼마나, 누가, 얼마나 비싼가."""
import pandas as pd

from config import BASE_FROM, ko


def run(ev, cases):
    t0 = pd.Timestamp(BASE_FROM, tz="Europe/Amsterdam")
    base = cases[cases["start"] >= t0]
    bev = ev[ev["case_id"].isin(base.index)]
    paid = base[base["outcome"] == "지급 완료"]

    rej = bev[bev["activity"].str.startswith("REJECTED") & (bev["activity"] != "REJECTED / EMPLOYEE")]
    by_role = rej["activity"].map(ko).value_counts()

    # 직원이 반려를 확인한 뒤 다시 제출하기까지 걸린 시간
    e = bev.copy()
    e["next"] = e.groupby("case_id")["activity"].shift(-1)
    e["gap"] = (e.groupby("case_id")["ts"].shift(-1) - e["ts"]).dt.total_seconds() / 86400
    resub = e[(e["activity"] == "REJECTED / EMPLOYEE") & (e["next"] == "SUBMITTED / EMPLOYEE")]["gap"]

    # 조직별 반려율 (건수 100건 이상)
    org = base.groupby("org").agg(cases=("rework", "size"), rework_rate=("rework", "mean"),
                                  median_days=("duration_d", "median"))
    org = org[org["cases"] >= 100].sort_values("rework_rate", ascending=False)

    med_no = paid.loc[~paid["rework"], "duration_d"].median()
    med_yes = paid.loc[paid["rework"], "duration_d"].median()
    # 재작업이 만든 추가 일수 = 같은 경로(예산책임자 경유 여부) 기준 중앙값 차이 × 건수
    extra = 0.0
    for hb, g in paid.groupby("has_budget"):
        m0 = g.loc[~g["rework"], "duration_d"].median()
        extra += (g.loc[g["rework"], "duration_d"] - m0).clip(lower=0).sum()

    return {
        "rework_rate": float(base["rework"].mean()),
        "abandon_after_reject": float((base["outcome"] == "반려 종료").sum() / max(base["rework"].sum(), 1)),
        "rejections_by_role": {k: int(v) for k, v in by_role.items()},
        "median_paid_no_rework": float(med_no), "median_paid_rework": float(med_yes),
        "rework_multiplier": float(med_yes / med_no),
        "resubmit_median": float(resub.median()), "resubmit_p90": float(resub.quantile(0.9)),
        "resubmit_over7_pct": float((resub > 7).mean()),
        "extra_days_total": float(extra),
        "org_top": org.head(6).reset_index().to_dict("records"),
        "org_bottom": org.tail(4).reset_index().to_dict("records"),
    }
