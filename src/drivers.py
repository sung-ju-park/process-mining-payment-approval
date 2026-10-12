"""처리 기간을 늘리는 요인: 다른 조건을 통제한 회귀분석 (log 처리일수)."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from config import BASE_FROM

WD = ["월", "화", "수", "목", "금", "토", "일"]


def run(cases):
    t0 = pd.Timestamp(BASE_FROM, tz="Europe/Amsterdam")
    d = cases[(cases["start"] >= t0) & (cases["outcome"] == "지급 완료")].copy()
    d = d[d["duration_d"] > 0]
    big = d["org"].value_counts()
    d["org_g"] = np.where(d["org"].isin(big[big >= 100].index), d["org"], "기타 조직")
    d["submit_day"] = pd.Categorical(d["submit_wd"].map(lambda i: WD[i]), categories=WD)
    d["rework_i"], d["budget_i"], d["pre_i"] = d["rework"].astype(int), d["has_budget"].astype(int), d["has_pre"].astype(int)
    d["y"] = np.log(d["duration_d"])
    m = smf.ols("y ~ rework_i + budget_i + log_amount + C(submit_day) + C(org_g)", data=d).fit(cov_type="HC3")
    eff = lambda name: {"pct": float(np.exp(m.params[name]) - 1),
                        "lo": float(np.exp(m.conf_int().loc[name, 0]) - 1),
                        "hi": float(np.exp(m.conf_int().loc[name, 1]) - 1),
                        "p": float(m.pvalues[name])}
    days = {f"C(submit_day)[T.{w}]": w for w in WD[1:]}
    return {
        "n": int(m.nobs), "r2": float(m.rsquared),
        "effects": {"반려 발생": eff("rework_i"), "예산책임자 승인 경유": eff("budget_i"),
                    "요청 금액 (log 1단위)": eff("log_amount")},
        "submit_day": {w: eff(k) for k, w in days.items() if k in m.params.index},
    }
