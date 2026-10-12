"""프로세스 발견: 변형(variant) 분석, 한글 프로세스 맵, Inductive Miner 모델 적합도."""
import subprocess
import warnings

import numpy as np
import pandas as pd

from config import BASE_FROM, FIG, ko

warnings.filterwarnings("ignore")
FONT = "Noto Sans CJK KR"


def variant_table(cases: pd.DataFrame) -> pd.DataFrame:
    vc = cases["variant"].value_counts()
    t = pd.DataFrame({"cases": vc})
    t["share"] = t["cases"] / t["cases"].sum()
    t["cum_share"] = t["share"].cumsum()
    t["median_days"] = cases.groupby("variant")["duration_d"].median().reindex(t.index)
    t["label"] = [" → ".join(ko(a) for a in v.split(" → ")) for v in t.index]
    return t.reset_index(drop=True)


def transitions(ev: pd.DataFrame) -> pd.DataFrame:
    e = ev.copy()
    e["next"] = e.groupby("case_id")["activity"].shift(-1)
    e["wait_d"] = (e.groupby("case_id")["ts"].shift(-1) - e["ts"]).dt.total_seconds() / 86400
    t = e.dropna(subset=["next"]).groupby(["activity", "next"])["wait_d"].agg(
        cases="size", median="median", mean="mean", p90=lambda s: s.quantile(0.9), total="sum").reset_index()
    t["share_of_wait"] = t["total"] / t["total"].sum()
    return t


def _color(days: float) -> str:
    # 대기 중앙값이 길수록 붉게
    if days >= 3:
        return "#C2410C"
    if days >= 1.5:
        return "#D97706"
    if days >= 0.5:
        return "#64748B"
    return "#94A3B8"


def process_map(ev: pd.DataFrame, cases: pd.DataFrame, path_stem, coverage=0.95, title=""):
    """상위 변형으로 전체 케이스의 coverage 비율을 덮는 범위만 그린다."""
    vt = cases["variant"].value_counts()
    keep_variants = vt[vt.cumsum() / vt.sum() <= coverage].index
    keep = cases.index[cases["variant"].isin(keep_variants)]
    e = ev[ev["case_id"].isin(keep)]
    t = transitions(e)
    starts = e.groupby("case_id")["activity"].first().value_counts()
    ends = e.groupby("case_id")["activity"].last().value_counts()
    node_n = e["activity"].value_counts()
    maxn = t["cases"].max()

    lines = [
        "digraph G {",
        f'  graph [rankdir=TB, bgcolor="white", fontname="{FONT}", nodesep=0.35, ranksep=0.45, pad=0.3, label="{title}", labelloc=t, fontsize=16];',
        f'  node [shape=box, style="rounded,filled", fontname="{FONT}", fontsize=11, color="#CBD5E1", fillcolor="#F8FAFC", penwidth=1.2, margin="0.18,0.08"];',
        f'  edge [fontname="{FONT}", fontsize=9, arrowsize=0.6];',
        '  __start [shape=circle, label="", width=0.22, style=filled, fillcolor="#1E3A8A", color="#1E3A8A"];',
        '  __end [shape=doublecircle, label="", width=0.18, style=filled, fillcolor="#1E3A8A", color="#1E3A8A"];',
    ]
    nid = {a: f"n{i}" for i, a in enumerate(node_n.index)}
    for a, n in node_n.items():
        sysfill = ', fillcolor="#EEF2FF", color="#A5B4FC"' if a in ("Request Payment", "Payment Handled") else ""
        lines.append(f'  {nid[a]} [label="{ko(a)}\\n{n:,}건"{sysfill}];')
    for a, n in starts.items():
        lines.append(f'  __start -> {nid[a]} [color="#94A3B8", penwidth={0.6 + 3.4 * n / maxn:.2f}, label=" {n:,}", fontcolor="#64748B"];')
    for a, n in ends.items():
        lines.append(f'  {nid[a]} -> __end [color="#94A3B8", penwidth={0.6 + 3.4 * n / maxn:.2f}, style=dashed];')
    for r in t.itertuples():
        col = _color(r.median)
        lab = f" {r.cases:,}건\\n 중앙 {r.median:.1f}일"
        lines.append(f'  {nid[r.activity]} -> {nid[r.next]} [color="{col}", fontcolor="{col}", penwidth={0.6 + 5.4 * r.cases / maxn:.2f}, label="{lab}"];')
    lines.append("}")
    dot = "\n".join(lines)
    FIG.mkdir(parents=True, exist_ok=True)
    (FIG / f"{path_stem}.dot").write_text(dot, encoding="utf-8")
    for fmt in ("svg", "png"):
        args = ["dot", f"-T{fmt}", str(FIG / f"{path_stem}.dot"), "-o", str(FIG / f"{path_stem}.{fmt}")]
        if fmt == "png":
            args.insert(2, "-Gdpi=170")
        subprocess.run(args, check=True)
    return {"cases_drawn": int(len(keep)), "coverage": float(len(keep) / len(cases)), "variants_drawn": int(len(keep_variants))}


def model_quality(ev: pd.DataFrame, noises=(0.0, 0.1, 0.2, 0.3)):
    """Inductive Miner로 노이즈 설정별 모델을 찾고, 적합도(fitness)와 정밀도(precision)의 균형(F1)이 가장 좋은 것을 고른다."""
    import pm4py
    df = pd.DataFrame({"case:concept:name": ev["case_id"], "concept:name": ev["activity"],
                       "time:timestamp": ev["ts"].dt.tz_convert("UTC")})
    rows, best = [], None
    for nz in noises:
        net, im, fm = pm4py.discover_petri_net_inductive(df, noise_threshold=nz)
        f = float(pm4py.fitness_token_based_replay(df, net, im, fm)["log_fitness"])
        p = float(pm4py.precision_token_based_replay(df, net, im, fm))
        f1 = 2 * f * p / (f + p)
        rows.append({"noise": nz, "fitness": f, "precision": p, "f1": f1})
        if best is None or f1 > best[0] + 1e-9:
            best = (f1, nz, net, im, fm)
    _, nz, net, im, fm = best
    pm4py.save_vis_bpmn(pm4py.convert_to_bpmn(net, im, fm), str(FIG / "bpmn_inductive.png"))
    chosen = next(r for r in rows if r["noise"] == nz)
    return {"noise_threshold": nz, "fitness": chosen["fitness"], "precision": chosen["precision"], "grid": rows}


def run(ev, cases):
    base = cases[cases["start"] >= pd.Timestamp(BASE_FROM, tz="Europe/Amsterdam")]
    bev = ev[ev["case_id"].isin(base.index)]
    vt = variant_table(base)
    out = {
        "n_variants": int(len(vt)),
        "top5_share": float(vt["share"].head(5).sum()),
        "n_variants_80": int((vt["cum_share"] < 0.80).sum() + 1),
        "n_variants_95": int((vt["cum_share"] < 0.95).sum() + 1),
        "variants_top": vt.head(8)[["label", "cases", "share", "median_days"]].to_dict("records"),
        "map": process_map(bev, base, "process_map", 0.95, "결재 프로세스 맵 (2018년 이후 주요 경로)"),
        "model": model_quality(bev),
    }
    vt.to_csv(FIG.parent / "variants.csv", index=False, encoding="utf-8-sig")
    return out


if __name__ == "__main__":
    from config import PROCESSED
    import json
    ev = pd.read_pickle(PROCESSED / "events.pkl"); cases = pd.read_pickle(PROCESSED / "cases.pkl")
    print(json.dumps(run(ev, cases), ensure_ascii=False, indent=1, default=str)[:2500])
