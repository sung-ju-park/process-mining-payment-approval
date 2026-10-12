"""규정 준수 점검: 결재 규칙을 이벤트 순서로 표현해 위반 건을 찾는다."""
import pandas as pd

from config import BASE_FROM

FINALS = {"FINAL_APPROVED / SUPERVISOR", "FINAL_APPROVED / DIRECTOR", "FINAL_APPROVED / BUDGET OWNER"}


def check(acts):
    first_final = next((i for i, a in enumerate(acts) if a in FINALS), None)
    req = [i for i, a in enumerate(acts) if a == "Request Payment"]
    pay = [i for i, a in enumerate(acts) if a == "Payment Handled"]
    return {
        "R1 최종승인 없이 지급": bool(pay) and first_final is None,
        "R2 최종승인 전 지급요청": bool(req) and (first_final is None or req[0] < first_final),
        "R3 지급요청 없이 지급완료": bool(pay) and not req,
        "R4 행정 검토 없이 최종승인": first_final is not None and "APPROVED / ADMINISTRATION" not in acts[:first_final]
                                     and "APPROVED / PRE_APPROVER" not in acts[:first_final],
        "R5 중복 지급": len(pay) > 1,
        "R6 반려 후 재제출 없이 승인": any(a.startswith("REJECTED / ") and a != "REJECTED / EMPLOYEE"
                                            and any(b in FINALS for b in acts[i + 1:])
                                            and "SUBMITTED / EMPLOYEE" not in acts[i + 1:] for i, a in enumerate(acts)),
    }


def run(ev, cases):
    t0 = pd.Timestamp(BASE_FROM, tz="Europe/Amsterdam")
    base = cases[cases["start"] >= t0]
    acts = ev[ev["case_id"].isin(base.index)].groupby("case_id")["activity"].apply(list)
    res = pd.DataFrame([check(a) for a in acts], index=acts.index)
    summary = res.sum().astype(int).to_dict()
    r4 = res.index[res["R4 행정 검토 없이 최종승인"]]
    return {
        "n_cases": int(len(res)),
        "violations": summary,
        "any_violation_pct": float(res.any(axis=1).mean()),
        "r4_amount_median": float(base.loc[r4, "amount"].median()) if len(r4) else None,
        "all_amount_median": float(base["amount"].median()),
        "r4_paid_median_days": float(base.loc[r4].query("outcome == '지급 완료'")["duration_d"].median()) if len(r4) else None,
    }
