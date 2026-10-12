"""README와 리포트에 쓰는 그래프."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from config import FIG, SCENARIO_LABEL

import os
from pathlib import Path

# 한글 글꼴 지정. 프로젝트의 fonts/ 폴더(있으면)나 FONT_DIR 환경변수의 글꼴을 먼저 등록하고,
# 없으면 운영체제에 설치된 한글 글꼴을 순서대로 찾는다. 찾지 못하면 한글이 네모로 깨지므로 바로 알린다.
for d in [Path(__file__).resolve().parent.parent / "fonts", Path(os.environ.get("FONT_DIR", "/nonexistent"))]:
    if d.is_dir():
        for f in d.glob("*.[ot]tf"):
            font_manager.fontManager.addfont(str(f))
KOREAN_FONTS = ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK JP", "Noto Sans CJK KR"]
_available = {f.name for f in font_manager.fontManager.ttflist}
_font = next((n for n in KOREAN_FONTS if n in _available), None)
if _font is None:
    raise RuntimeError("한글 글꼴을 찾지 못했습니다. fonts/ 폴더에 한글 글꼴(.ttf)을 넣거나 맑은 고딕을 설치하세요.")
plt.rcParams["font.family"] = _font
plt.rcParams.update({"axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#CBD5E1", "axes.labelcolor": "#334155", "xtick.color": "#475569",
                     "ytick.color": "#475569", "font.size": 10.5, "figure.dpi": 150})
INK, ACC, WARN, GREY = "#1B2333", "#2B59C3", "#C2410C", "#CBD5E1"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def wait_share(perf):
    rows = perf["top_transitions"][:7][::-1]
    labels = [f"{r['from_ko']} → {r['to_ko']}" for r in rows]
    vals = [r["share_of_wait"] * 100 for r in rows]
    cols = [WARN if ("지급" in r["to_ko"]) else ACC for r in rows]
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    ax.barh(labels, vals, color=cols, height=0.62)
    for i, (v, r) in enumerate(zip(vals, rows)):
        ax.text(v + 0.6, i, f"{v:.1f}%  (중앙 {r['median']:.1f}일)", va="center", fontsize=9.5, color=INK)
    ax.set_xlabel("전체 대기 시간 중 비중 (%)")
    ax.set_xlim(0, max(vals) * 1.45)
    ax.set_title("시간은 어디서 새는가: 단계 사이 대기 시간 비중", loc="left", fontsize=12.5, color=INK, pad=10)
    _save(fig, "wait_share")


def payment_batch(perf):
    wd = ["월", "화", "수", "목", "금", "토", "일"]
    pay = [perf["payment_weekday"].get(d, 0) for d in wd]
    req = [perf["request_weekday"].get(d, 0) for d in wd]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.2), sharey=False)
    axes[0].bar(wd, req, color=GREY)
    axes[0].set_title("지급 요청이 올라오는 요일", loc="left", fontsize=11, color=INK)
    axes[1].bar(wd, pay, color=[WARN if p > 0 and d in ("월", "목") else GREY for d, p in zip(wd, pay)])
    axes[1].set_title("실제 지급이 처리되는 요일", loc="left", fontsize=11, color=INK)
    for ax in axes:
        ax.set_ylabel("건수")
    fig.suptitle("요청은 매일 오지만, 지급은 월·목 17시에만 처리된다", x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.tight_layout()
    _save(fig, "payment_batch")


def cutoff_search(wi):
    srch = wi["validation"]["cutoff_search"]
    hs, vs = list(map(int, srch.keys())), [v * 100 for v in srch.values()]
    fig, ax = plt.subplots(figsize=(7.6, 3.1))
    ax.plot(hs, vs, color=ACC, marker="o", lw=2)
    best = wi["validation"]["cutoff_h"]
    ax.scatter([best], [srch[best] * 100], s=110, color=WARN, zorder=3)
    ax.annotate(f"24시간 마감 가정 시\n실제 지급 시각 {srch[best]*100:.1f}% 재현", (best, srch[best] * 100),
                xytext=(26, 56), fontsize=9.5, color=WARN,
                arrowprops=dict(arrowstyle="-", color=WARN))
    ax.annotate(f"마감 없음 가정: {srch[0]*100:.1f}%", (0, srch[0] * 100), xytext=(4, srch[0] * 100 - 9),
                fontsize=9.5, color="#64748B")
    ax.set_xlabel("지급 요청 마감 (배치 몇 시간 전까지 올라와야 포함되는가)")
    ax.set_ylabel("재현율 (%)")
    ax.set_ylim(40, 100)
    ax.set_title("숨은 규칙 찾기: 지급 마감 시간에 따른 재현율", loc="left", fontsize=12.5, color=INK, pad=10)
    _save(fig, "cutoff_search")


def scenarios(wi):
    sc = wi["scenarios"]
    names = list(sc.keys())
    med = [sc[n]["median"] for n in names]
    w7 = [sc[n]["within7"] * 100 for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    cols = [GREY] + [ACC] * (len(names) - 2) + [WARN]
    short = [SCENARIO_LABEL.get(n, n) for n in names]
    axes[0].barh(short[::-1], med[::-1], color=cols[::-1], height=0.6)
    for i, v in enumerate(med[::-1]):
        axes[0].text(v + 0.15, i, f"{v:.1f}일", va="center", fontsize=9.5)
    axes[0].set_title("지급 완료까지 걸리는 기간 (중앙값)", loc="left", fontsize=11, color=INK)
    axes[0].set_xlim(0, max(med) * 1.25)
    axes[1].barh(short[::-1], w7[::-1], color=cols[::-1], height=0.6)
    for i, v in enumerate(w7[::-1]):
        axes[1].text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9.5)
    axes[1].set_title("7일 안에 지급되는 비율", loc="left", fontsize=11, color=INK)
    axes[1].set_xlim(0, 100)
    axes[1].set_yticklabels([])
    fig.suptitle("개선 시나리오 시뮬레이션 (2018년 이후 지급 완료 건)", x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.tight_layout()
    _save(fig, "scenarios")


def drivers_plot(dr):
    items = list(dr["effects"].items()) + [(f"{k}요일 제출 (월요일 대비)", v) for k, v in dr["submit_day"].items()
                                           if k in ("목", "금")]
    items = items[::-1]
    fig, ax = plt.subplots(figsize=(7.8, 3.2))
    for i, (k, v) in enumerate(items):
        c = WARN if v["pct"] > 0.3 else ACC
        ax.plot([v["lo"] * 100, v["hi"] * 100], [i, i], color=c, lw=2.2)
        ax.scatter([v["pct"] * 100], [i], color=c, s=50, zorder=3)
        ax.text(v["hi"] * 100 + 2, i, f"+{v['pct']*100:.0f}%", va="center", fontsize=9.5, color=INK)
    ax.axvline(0, color="#94A3B8", lw=1)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([k for k, _ in items])
    ax.set_xlabel("처리 기간 증가율 (%, 95% 신뢰구간)")
    ax.set_title("다른 조건을 같게 했을 때, 무엇이 기간을 늘리나", loc="left", fontsize=12.5, color=INK, pad=10)
    _save(fig, "drivers")


def quarterly(perf):
    q = perf["quarterly"]
    lab = [r["quarter"].replace("Q", "\nQ") for r in q]
    a = [r["결재"] for r in q]; b = [r["지급요청 대기"] for r in q]; c = [r["지급 대기"] for r in q]
    fig, ax = plt.subplots(figsize=(8.4, 3.3))
    ax.bar(lab, a, color=ACC, label="결재")
    ax.bar(lab, b, bottom=a, color="#93A9E6", label="지급요청 대기")
    ax.bar(lab, c, bottom=[x + y for x, y in zip(a, b)], color=WARN, label="지급 대기")
    ax2 = ax.twinx()
    ax2.plot(lab, [r["예산책임자경유"] * 100 for r in q], color=INK, marker="o", lw=1.6, label="예산책임자 경유율")
    ax2.set_ylabel("예산책임자 경유율 (%)")
    ax2.spines["right"].set_visible(True)
    ax.set_ylabel("구간별 중앙값 (일)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4)
    ax.set_ylim(0, 10)
    ax2.set_ylim(0, 50)
    ax.set_title("분기별 구간 중앙값: 지급 대기는 2년 내내 그대로였다", loc="left", fontsize=12.5, color=INK, pad=30)
    _save(fig, "quarterly")


def all_figs(perf, dr, wi):
    wait_share(perf); payment_batch(perf); cutoff_search(wi); scenarios(wi); drivers_plot(dr); quarterly(perf)
