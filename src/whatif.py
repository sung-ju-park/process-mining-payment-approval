"""개선 시나리오 시뮬레이션.

1) 먼저 현재 지급 규칙(월·목 17시 배치)으로 실제 지급 시각을 재현해 모델을 검증한다.
2) 검증된 규칙을 바꿔(매일 지급, 지급요청 자동 생성, 재제출 지연 단축) 처리 기간이 어떻게 바뀌는지 계산한다.
"""
import numpy as np
import pandas as pd

from config import BASE_FROM

BATCH_HOUR = 17
CUTOFF_H = 24  # 데이터에서 찾은 규칙: 지급 요청이 배치 24시간 전까지 올라와야 그 배치에 포함된다


def next_batch(ts: pd.Timestamp, days: set, cutoff_h: float = CUTOFF_H) -> pd.Timestamp:
    """ts 이후, 마감(cutoff) 조건을 만족하는 가장 가까운 지급 배치 시각 (지정 요일 17시)."""
    ts = ts + pd.Timedelta(hours=cutoff_h)
    cand = ts.normalize() + pd.Timedelta(hours=BATCH_HOUR)
    if cand < ts:
        cand += pd.Timedelta(days=1)
    while cand.dayofweek not in days:
        cand += pd.Timedelta(days=1)
    return cand


def run(ev, cases, seg):
    t0 = pd.Timestamp(BASE_FROM, tz="Europe/Amsterdam")
    s = seg[seg["first"] >= t0].copy()

    # 1) 현재 규칙 재현: 마감 시간을 0~72시간으로 바꿔 가며 실제 지급 시각과 가장 잘 맞는 값을 찾는다
    def match(cutoff):
        sim = s["req"].map(lambda t: next_batch(t, {0, 3}, cutoff))
        return float(((sim - s["paid"]).dt.total_seconds().abs() / 3600 <= 1).mean())
    search = {h: match(h) for h in [0, 6, 12, 18, 24, 30, 36, 48, 60, 72]}
    validation = {"cutoff_search": search, "cutoff_h": CUTOFF_H, "same_batch_pct": search[CUTOFF_H],
                  "naive_pct": search[0]}

    # 재제출 지연 (반려 확인 → 재제출 간격)
    e = ev[ev["case_id"].isin(s.index)].copy()
    e["next"] = e.groupby("case_id")["activity"].shift(-1)
    e["gap"] = (e.groupby("case_id")["ts"].shift(-1) - e["ts"]).dt.total_seconds() / 86400
    gaps = e[(e["activity"] == "REJECTED / EMPLOYEE") & (e["next"] == "SUBMITTED / EMPLOYEE")]["gap"]
    gap_case = e.loc[gaps.index, "case_id"]
    # 재제출마다 개별로 1일 상한을 적용하고, 줄어든 시간을 케이스별로 더한다
    # (케이스의 재제출 대기를 모두 합친 뒤 1일로 자르면, 재제출이 여러 번인 건의 절감 효과가 과대 계산됨)
    per_gap_cut = (gaps - gaps.clip(upper=1.0)).clip(lower=0)
    s["resub_cut"] = per_gap_cut.groupby(gap_case).sum().reindex(s.index).fillna(0.0)

    def total(final, req, paid, resub_cut=0.0):
        return ((paid - s["first"]).dt.total_seconds() / 86400) - resub_cut

    base_tot = total(s["final"], s["req"], s["paid"])
    sc = {}
    # S1 매일 지급 (평일 매일 17시)
    p1 = s["req"].map(lambda t: next_batch(t, {0, 1, 2, 3, 4}))
    sc["S1 지급 배치를 매일(평일)로"] = total(s["final"], s["req"], p1)
    # S2 최종승인 즉시 지급요청 자동 생성 (현재 배치 유지)
    p2 = s["final"].map(lambda t: next_batch(t, {0, 3}))
    sc["S2 최종승인 즉시 지급요청"] = total(s["final"], s["final"], p2)
    # S3 재제출 지연을 최대 1일로 (반려 안내·체크리스트 개선 가정)
    cut = s["resub_cut"]
    sc["S3 재제출 지연 최대 1일"] = base_tot - cut
    # S1+S2+S3
    p4 = s["final"].map(lambda t: next_batch(t, {0, 1, 2, 3, 4}))
    sc["S1+S2+S3 함께"] = total(s["final"], s["final"], p4) - cut

    def stats(x):
        return {"median": float(x.median()), "mean": float(x.mean()), "p90": float(x.quantile(0.9)),
                "within7": float((x <= 7).mean())}

    res = {"현재": stats(base_tot)}
    res.update({k: stats(v) for k, v in sc.items()})
    saved_days = {k: float((base_tot - v).sum()) for k, v in sc.items()}
    return {"n": int(len(s)), "validation": validation, "scenarios": res, "saved_case_days": saved_days}
