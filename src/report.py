"""분석 결과를 한 장짜리 HTML 리포트로 만든다 (그림 포함, 단일 파일)."""
import base64

from config import FIG, OUT, SCENARIO_LABEL


def img(name, alt=""):
    data = base64.b64encode((FIG / f"{name}.png").read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{data}" alt="{alt}"></figure>'


def svg(name):
    s = (FIG / f"{name}.svg").read_text(encoding="utf-8")
    return f'<figure class="map">{s[s.index("<svg"):]}</figure>'


def pct(x, d=0):
    return f"{x*100:.{d}f}%"


def build(r):
    ov, disc, perf, rw, conf, dr, wi = (r[k] for k in ["overview", "discovery", "performance", "rework",
                                                       "conformance", "drivers", "whatif"])
    sc = wi["scenarios"]
    cur, best = sc["현재"], sc["S1+S2+S3 함께"]
    seg_m = perf["segment_median"]
    same = {str(k): v for k, v in perf["same_orgs_by_year"].items()}
    be = {str(k): v for k, v in perf["budget_effect"].items()}
    eff = dr["effects"]
    tops = "".join(
        f"<tr><td>{v['label']}</td><td class='n'>{v['cases']:,}</td><td class='n'>{pct(v['share'],1)}</td>"
        f"<td class='n'>{v['median_days']:.1f}일</td></tr>" for v in disc["variants_top"][:6])
    viol = "".join(f"<tr><td>{k}</td><td class='n'>{v:,}건</td></tr>" for k, v in conf["violations"].items())
    scen_rows = "".join(
        f"<tr><td>{SCENARIO_LABEL.get(k, k)}</td><td class='n'>{v['median']:.1f}일</td><td class='n'>{v['mean']:.1f}일</td>"
        f"<td class='n'>{v['p90']:.1f}일</td><td class='n'>{pct(v['within7'])}</td></tr>" for k, v in sc.items())
    org_rows = "".join(
        f"<tr><td>{o['org'].replace('organizational unit ', '조직 ')}</td><td class='n'>{o['cases']:,}</td>"
        f"<td class='n'>{pct(o['rework_rate'],1)}</td><td class='n'>{o['median_days']:.1f}일</td></tr>"
        for o in rw["org_top"][:3] + rw["org_bottom"][-3:])
    grid = "".join(
        f"<tr><td>{g['noise']}</td><td class='n'>{g['fitness']:.3f}</td><td class='n'>{g['precision']:.3f}</td>"
        f"<td class='n'>{g['f1']:.3f}</td></tr>" for g in disc["model"]["grid"])
    prec = disc["model"]["precision"]
    rej_role = ", ".join(f"{k} {v:,}건" for k, v in rw["rejections_by_role"].items())
    admin_share = rw["rejections_by_role"].get("반려 (행정)", 0) / sum(rw["rejections_by_role"].values())

    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>지급 요청 결재 프로세스 진단 | 프로세스 마이닝</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root {{ --ink:#1B2333; --sub:#5A6475; --line:#E2E8F0; --acc:#2B59C3; --acc-soft:#EEF3FC; --warn:#C2410C; --warn-soft:#FDF1EA; --bg:#F7F8FA; }}
* {{ box-sizing:border-box; }}
body {{ font-feature-settings:"calt" 0, "case" 0, "tnum" 0; margin:0; background:var(--bg); color:var(--ink); font-family:"Pretendard","Malgun Gothic",system-ui,sans-serif; line-height:1.7; font-size:15.5px; word-break:keep-all; }}
.wrap {{ max-width:900px; margin:0 auto; padding:56px 24px 96px; }}
header .kicker {{ color:var(--acc); font-weight:700; font-size:14px; }}
h1 {{ font-size:32px; line-height:1.3; letter-spacing:-0.02em; margin:8px 0 12px; }}
.lead {{ font-size:17px; color:#334155; max-width:62ch; }}
.meta {{ margin-top:14px; color:var(--sub); font-size:13.5px; }}
.summary {{ margin-top:36px; background:#fff; border:1px solid var(--line); border-radius:14px; padding:28px; }}
.summary h2 {{ margin-top:0; }}
.kpis {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:18px 0 6px; }}
.kpi {{ border-radius:10px; padding:16px; background:var(--bg); }}
.kpi b {{ display:block; font-size:28px; letter-spacing:-0.02em; }}
.kpi span {{ font-size:13.5px; color:var(--sub); }}
.kpi.warn b {{ color:var(--warn); }} .kpi.acc b {{ color:var(--acc); }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:16px; }}
.two h3 {{ margin:0 0 6px; font-size:15px; }}
ol {{ margin:6px 0 0; padding-left:20px; }} ol li {{ margin:6px 0; }}
section {{ margin-top:56px; }}
h2 {{ font-size:22px; letter-spacing:-0.01em; margin:0 0 6px; }}
.num {{ color:var(--acc); font-weight:700; font-size:13px; letter-spacing:0.04em; }}
p {{ margin:10px 0; max-width:70ch; }}
figure {{ margin:18px 0; background:#fff; border:1px solid var(--line); border-radius:12px; padding:14px; }}
figure img {{ width:100%; display:block; }}
figure.map {{ text-align:center; }} figure.map img {{ max-width:560px; margin:0 auto; }}
table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; font-size:14px; margin:14px 0; }}
th, td {{ padding:9px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:#F1F4F9; font-weight:600; color:#334155; }}
td.n {{ text-align:right; white-space:nowrap; }}
.callout {{ background:var(--acc-soft); border-radius:10px; padding:14px 16px; margin:14px 0; }}
.callout.warn {{ background:var(--warn-soft); }}
.note {{ color:var(--sub); font-size:13.5px; }}
footer {{ margin-top:64px; color:var(--sub); font-size:13px; border-top:1px solid var(--line); padding-top:18px; }}
@media (max-width:720px) {{ .kpis, .two {{ grid-template-columns:1fr; }} h1 {{ font-size:26px; }} }}
</style></head>
<body><div class="wrap">

<header>
  <div class="kicker">Process Mining Case Study</div>
  <h1>지급 요청 결재 프로세스 진단</h1>
  <p class="lead">한 대학의 비용 지급 요청 {ov['cases']:,}건, 이벤트 {ov['events']:,}개가 남긴 실제 업무 시스템 로그로 업무 흐름을 복원하고, 처리가 늦어지는 원인을 찾아 개선 효과를 시뮬레이션했습니다.</p>
  <div class="meta">데이터: BPI Challenge 2020, Request For Payment (실제 기업 로그, 공개 데이터) · 기간 {ov['period'][0]} ~ {ov['period'][1]} · 분석 기준: 2018년 이후 {ov['base_cases']:,}건</div>
</header>

<div class="summary">
  <h2>요약</h2>
  <div class="kpis">
    <div class="kpi warn"><b>{pct(perf['post_approval_wait_share'])}</b><span>전체 대기 시간 중 <br>최종 승인 이후에 생기는 비중</span></div>
    <div class="kpi"><b>{cur['median']:.1f}일 → {best['median']:.1f}일</b><span>세 가지 개선을 함께 적용했을 때 <br>지급까지 걸리는 기간 (중앙값)</span></div>
    <div class="kpi acc"><b>{pct(cur['within7'])} → {pct(best['within7'])}</b><span>7일 안에 지급되는 비율</span></div>
  </div>
  <div class="two">
    <div><h3>핵심 발견</h3><ol>
      <li>결재자보다 <b>결재가 끝난 뒤</b>가 더 오래 걸린다. 지급은 <b>월·목 17시에만</b> 처리되고, 요청은 <b>배치 24시간 전까지</b> 올라와야 포함된다.</li>
      <li>2018년부터 생긴 <b>예산책임자 승인</b>을 거치면 결재 구간이 {be['False']['결재']:.1f}일에서 {be['True']['결재']:.1f}일로 늘어난다.</li>
      <li><b>반려가 한 번이라도 생기면</b> 다른 조건이 같아도 처리 기간이 {pct(eff['반려 발생']['pct'])} 늘어나고, 반려된 건의 {pct(rw['abandon_after_reject'])}는 다시 제출되지 않는다.</li>
    </ol></div>
    <div><h3>제안</h3><ol>
      <li>최종 승인 즉시 지급 요청이 자동으로 만들어지게 한다. <span class="note">(중앙값 {sc['S2 최종승인 즉시 지급요청']['median']:.1f}일)</span></li>
      <li>지급 배치를 주 2회에서 평일 매일로 늘린다. <span class="note">(중앙값 {sc['S1 지급 배치를 매일(평일)로']['median']:.1f}일)</span></li>
      <li>반려율이 높은 조직부터 반려 사유를 표준화하고 재제출을 안내한다. <span class="note">(지연 상위 10% 단축)</span></li>
    </ol></div>
  </div>
</div>

<section>
  <div class="num">01</div><h2>데이터와 분석 범위</h2>
  <p>로그에는 지급 요청 한 건이 제출되고, 행정·예산책임자·관리자의 승인이나 반려를 거쳐, 시스템이 지급을 처리하기까지의 모든 단계가 시각과 함께 남아 있습니다. 결과는 지급 완료 {ov['outcomes'].get('지급 완료',0):,}건, 반려로 종료 {ov['outcomes'].get('반려 종료',0):,}건, 임시저장만 된 건 {ov['outcomes'].get('임시저장만',0):,}건, 진행 중 {ov['outcomes'].get('진행 중',0):,}건입니다.</p>
  <div class="callout"><b>왜 2018년 이후를 기준으로 삼았나.</b> 2017년 로그는 10개 조직, 분기당 200~400건뿐이지만 2018년부터 36개 조직, 분기당 1,200~1,700건으로 늘어납니다. 같은 시기에 예산책임자 승인 단계(2017년 0% → 2018년 {pct(perf['budget_share'])})도 새로 등장합니다. 두 시기를 섞으면 프로세스 변화와 대상 조직 변화가 구분되지 않아 분석은 2018년 이후로 맞췄습니다. 2017년 기록에는 별도의 한계도 있어 5절에 따로 적었습니다.</div>
</section>

<section>
  <div class="num">02</div><h2>실제 업무 흐름</h2>
  <p>2018년 이후 결재 경로는 {disc['n_variants']}가지지만, <b>상위 {disc['n_variants_80']}개 경로가 80%</b>, 상위 5개가 {pct(disc['top5_share'])}를 차지합니다. 아래 맵은 상위 경로로 전체의 {pct(disc['map']['coverage'])}를 그린 것입니다. 선이 굵을수록 많이 지나가고, 붉을수록 다음 단계까지 오래 기다리는 구간입니다.</p>
  {img('process_map', '결재 프로세스 맵').replace('<figure>', '<figure class="map">')}
  <table><tr><th>결재 경로</th><th>건수</th><th>비중</th><th>처리 기간 중앙값</th></tr>{tops}</table>
  <p>로그에서 프로세스 모델을 자동으로 찾는 Inductive Miner도 적용했습니다. 노이즈 설정을 바꿔 가며 적합도(실제 로그를 모델이 얼마나 재현하나)와 정밀도(모델이 실제에 없는 경로를 얼마나 적게 허용하나)를 비교했습니다.</p>
  <table><tr><th>노이즈 설정</th><th>적합도</th><th>정밀도</th><th>균형 (F1)</th></tr>{grid}</table>
  <p class="note">적합도는 0.98 수준으로 높지만 정밀도는 {prec:.2f}에서 더 오르지 않았습니다. 반려 후 재제출 같은 반복 구간 때문에 모델이 실제보다 넓은 경로를 허용하는 구조입니다. 그래서 이 분석은 자동 생성 모델보다, 실제 경로(변형)와 로그에서 직접 계산한 위의 프로세스 맵을 중심으로 진행했습니다.</p>
</section>

<section>
  <div class="num">03</div><h2>시간은 어디서 새는가</h2>
  <p>단계 사이의 대기 시간을 모두 더해 어느 구간이 얼마나 차지하는지 봤습니다. 가장 큰 두 구간은 결재자가 아니라 시스템 쪽입니다. <b>"최종 승인 → 지급 요청"과 "지급 요청 → 지급 완료"가 전체 대기 시간의 {pct(perf['post_approval_wait_share'],1)}</b>를 차지합니다.</p>
  {img('wait_share', '단계 사이 대기 시간 비중')}
  <p>지급 완료 건을 세 구간으로 나누면 중앙값 기준 결재 {seg_m['결재']:.1f}일, 지급 요청 대기 {seg_m['지급요청 대기']:.1f}일, 지급 대기 {seg_m['지급 대기']:.1f}일입니다. 2018년 이후 지급 완료까지 중앙값은 {perf['paid_median']:.1f}일, 상위 10%는 {perf['paid_p90']:.1f}일 이상 걸렸고, 7일 안에 끝난 건은 {pct(perf['within7_pct'])}뿐입니다.</p>
</section>

<section>
  <div class="num">04</div><h2>지급 배치와 숨은 마감 규칙</h2>
  <p>지급 요청은 평일 내내 올라오지만, 지급 처리는 <b>{pct(perf['payment_batch_share'],1)}가 월요일과 목요일 17시</b>에 몰려 있습니다. 주 2회 배치로 지급하는 구조입니다.</p>
  {img('payment_batch', '요일별 지급 요청과 지급 처리')}
  <p>그런데 "요청 후 다음 월·목 17시에 지급된다"고 가정하면 실제 지급 시각과 {pct(wi['validation']['naive_pct'],1)}만 일치했습니다. 배치 직전에 올라온 요청은 그 배치에 들어가지 못하는 마감 규칙이 있다고 보고, 마감 시간을 0~72시간으로 바꿔 가며 실제와 비교했습니다. <b>배치 24시간 전까지 올라온 요청만 포함된다</b>고 할 때 재현율이 {pct(wi['validation']['same_batch_pct'],1)}로 가장 높았습니다.</p>
  {img('cutoff_search', '마감 시간별 재현율')}
  <div class="callout">이 규칙 때문에 수요일 오후 5시 이후에 올라온 지급 요청은 다음 날인 목요일 배치에 들어가지 못하고 다음 주 월요일에 지급됩니다. 실제로 반려 없이 처리된 건 중 <b>목요일 제출 건은 {perf['submit_weekday_median']['목']:.1f}일, 월요일 제출 건은 {perf['submit_weekday_median']['월']:.1f}일</b>이 걸렸습니다. 9절의 시나리오는 이렇게 재현이 확인된 규칙 위에서 계산했습니다.</div>
</section>

<section>
  <div class="num">05</div><h2>예산책임자 승인과 결재 구간</h2>
  <p>분기별로 구간을 나눠 보면 지급 대기는 2년 내내 약 3.2일로 그대로이고, 2018년부터 예산책임자 승인 단계(경유율 약 35%)가 등장하면서 결재 구간이 길어졌습니다.</p>
  {img('quarterly', '분기별 구간 중앙값과 예산책임자 경유율')}
  <p>2018년 이후 예산책임자 승인을 거치는 건은 결재 구간이 <b>{be['False']['결재']:.1f}일 → {be['True']['결재']:.1f}일</b>로 길어집니다. 같은 기간 안에서 비교한 것이라 이 차이는 경로 자체의 효과로 볼 수 있습니다.</p>
  <div class="callout warn"><b>2017년과의 비교는 조심해서 봐야 합니다.</b> 두 해 모두 있는 조직끼리 비교하면 결재 구간 중앙값이 {same['2017']['결재']:.1f}일에서 {same['2018']['결재']:.1f}일로 늘어난 것처럼 보입니다. 그런데 2017년에는 제출과 최종 승인이 1분 안에 함께 기록된 건이 39%였고 2018년에는 0%였습니다. 실제로 결재가 1분 만에 끝났다기보다, 2017년에는 결재가 다른 방식으로 처리되고 기록만 한꺼번에 남았을 가능성이 큽니다. 그래서 연도 간 증가 폭은 결론에 쓰지 않고, 결론은 2018년 안의 비교로만 냈습니다.</div>
</section>

<section>
  <div class="num">06</div><h2>반려와 재작업</h2>
  <p>2018년 이후 <b>{pct(rw['rework_rate'],1)}</b>가 한 번 이상 반려됐습니다. 반려는 {rej_role}로, <b>{pct(admin_share)}가 행정 단계</b>에서 나옵니다. 반려된 건의 <b>{pct(rw['abandon_after_reject'])}는 다시 제출되지 않고</b> 끝났고, 다시 제출하는 경우에도 중앙값은 {rw['resubmit_median']:.1f}일이지만 {pct(rw['resubmit_over7_pct'])}는 일주일 넘게 걸렸습니다.</p>
  <p>지급까지 간 건만 보면 반려가 없으면 중앙값 {rw['median_paid_no_rework']:.1f}일, 있으면 {rw['median_paid_rework']:.1f}일로 약 {rw['rework_multiplier']:.1f}배입니다. 반려율은 조직마다 크게 달라, 사람보다 조직별 신청 관행이나 안내 방식에서 원인을 찾을 여지가 큽니다.</p>
  <table><tr><th>조직 (100건 이상, 반려율 상·하위)</th><th>건수</th><th>반려율</th><th>처리 기간 중앙값</th></tr>{org_rows}</table>
</section>

<section>
  <div class="num">07</div><h2>무엇이 기간을 늘리나</h2>
  <p>반려, 예산책임자 경유, 요청 금액, 제출 요일, 조직을 함께 넣은 회귀분석(log 처리일수, n={dr['n']:,})으로 각 요인의 효과를 다른 조건을 통제한 상태에서 추정했습니다.</p>
  {img('drivers', '요인별 처리 기간 증가율')}
  <p>반려는 <b>+{pct(eff['반려 발생']['pct'])}</b>, 예산책임자 경유는 <b>+{pct(eff['예산책임자 승인 경유']['pct'])}</b>, 목·금요일 제출은 월요일보다 약 4할 길었습니다. 반면 <b>요청 금액의 영향은 거의 없었습니다</b>(log 금액 1단위당 +{pct(eff['요청 금액 (log 1단위)']['pct'],1)}). 금액이 커서 늦어지는 것이 아니라 경로와 시점이 기간을 정한다는 뜻입니다.</p>
  <p class="note">설명력(R²)은 {dr['r2']:.2f}입니다. 결재자의 부재, 휴가, 반려 사유 같은 정보가 로그에 없기 때문에 개별 건의 기간을 맞히는 모델이 아니라, 요인별 효과의 크기와 방향을 비교하는 용도로 해석해야 합니다.</p>
</section>

<section>
  <div class="num">08</div><h2>규정 준수 점검</h2>
  <p>결재 규칙을 이벤트 순서로 표현해 2018년 이후 {conf['n_cases']:,}건을 점검했습니다. 최종 승인 없이 지급되거나, 승인 전에 지급이 요청되거나, 반려 후 재제출 없이 승인된 건은 없었습니다. <b>통제는 잘 작동하고 있고, 문제는 속도</b>입니다.</p>
  <table><tr><th>점검 규칙</th><th>위반</th></tr>{viol}</table>
</section>

<section>
  <div class="num">09</div><h2>개선안과 기대효과</h2>
  <p>4절에서 재현율을 확인한 지급 규칙(월·목 17시, 24시간 마감) 위에서 규칙을 하나씩 바꿔 2018년 이후 지급 완료 {wi['n']:,}건의 처리 기간을 다시 계산했습니다.</p>
  {img('scenarios', '개선 시나리오별 처리 기간')}
  <table><tr><th>시나리오</th><th>중앙값</th><th>평균</th><th>상위 10%</th><th>7일 내 지급</th></tr>{scen_rows}</table>
  <div class="callout warn"><b>가장 효과가 큰 것은 S2입니다.</b> 최종 승인 후 지급 요청이 만들어지기까지의 대기를 없애면, 요청이 더 일찍 마감 전에 들어가 이번 배치에 포함되는 효과까지 생깁니다. 시스템 설정 변경만으로 가능한 개선이라 비용 대비 효과도 큽니다. S3는 반려 건이 전체의 일부라 중앙값은 거의 그대로지만, 오래 걸리는 건(상위 10%)을 줄이는 효과가 있습니다.</div>
</section>

<section>
  <div class="num">10</div><h2>한계와 다음 단계</h2>
  <ul>
    <li>로그에 반려 사유가 없어, 반려의 원인은 조직별 차이까지만 확인했습니다. 반려 사유 데이터가 있다면 사유별로 사전 체크리스트를 만들 수 있습니다.</li>
    <li>담당자가 익명화(STAFF MEMBER)되어 있어 사람별 업무량이나 결재자 부재의 영향은 볼 수 없었습니다.</li>
    <li>2017년 로그는 제출과 최종 승인이 1분 안에 함께 기록된 건이 39%(2018년 0%)로 기록 방식이 달랐던 것으로 보여, 연도 간 비교는 결론에 쓰지 않았습니다.</li>
    <li>시뮬레이션의 지급 규칙 재현율은 {pct(wi['validation']['same_batch_pct'],1)}입니다. 나머지는 공휴일 등 예외로 보이며, 시나리오 수치는 이 범위 안에서의 추정입니다.</li>
    <li>다음 단계로는 예산책임자 승인이 필요한 조건(금액, 프로젝트 등)을 찾아, 꼭 필요한 건만 거치게 하는 규칙을 검토할 수 있습니다.</li>
  </ul>
</section>

<footer>박성주 · 데이터: van Dongen, B.F. (2020) BPI Challenge 2020: Request For Payment, 4TU.ResearchData · 분석 도구: Python, pandas, pm4py, statsmodels, Graphviz</footer>
</div></body></html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")
