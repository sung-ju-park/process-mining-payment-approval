"""경로와 공통 설정."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
# 4TU 원본(RequestForPayment.xes.gz)과 압축을 푼 파일(.xes) 모두 지원
RAW = next((p for p in [RAW_DIR / "RequestForPayment.xes.gz", RAW_DIR / "RequestForPayment.xes"] if p.exists()),
           RAW_DIR / "RequestForPayment.xes.gz")
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"

# 분석 기준 기간: 2018년부터 전 조직으로 확대되고 결재 구조가 바뀌어 이 기간을 기준으로 삼는다
BASE_FROM = "2018-01-01"

# 활동 이름 축약 (로그 원문 → 리포트 표기)
def short(act: str) -> str:
    return act.replace("Request For Payment ", "").replace(" by ", " / ")

KO = {
    "SUBMITTED / EMPLOYEE": "제출 (직원)",
    "SAVED / EMPLOYEE": "임시저장 (직원)",
    "APPROVED / ADMINISTRATION": "승인 (행정)",
    "APPROVED / PRE_APPROVER": "승인 (사전승인자)",
    "APPROVED / BUDGET OWNER": "승인 (예산책임자)",
    "APPROVED / SUPERVISOR": "승인 (관리자)",
    "FINAL_APPROVED / SUPERVISOR": "최종승인 (관리자)",
    "FINAL_APPROVED / DIRECTOR": "최종승인 (부서장)",
    "FINAL_APPROVED / BUDGET OWNER": "최종승인 (예산책임자)",
    "REJECTED / ADMINISTRATION": "반려 (행정)",
    "REJECTED / SUPERVISOR": "반려 (관리자)",
    "REJECTED / BUDGET OWNER": "반려 (예산책임자)",
    "REJECTED / PRE_APPROVER": "반려 (사전승인자)",
    "REJECTED / MISSING": "반려 (역할 미상)",
    "REJECTED / EMPLOYEE": "반려 확인 (직원)",
    "FOR_APPROVAL / ADMINISTRATION": "승인 요청 (행정)",
    "FOR_APPROVAL / SUPERVISOR": "승인 요청 (관리자)",
    "Request Payment": "지급 요청 (시스템)",
    "Payment Handled": "지급 완료 (시스템)",
}

def ko(act: str) -> str:
    return KO.get(act, act)


# 시나리오 표시 이름 (그래프·표·README 공통)
SCENARIO_LABEL = {
    "현재": "현재",
    "S1 지급 배치를 매일(평일)로": "S1 평일 매일 지급",
    "S2 최종승인 즉시 지급요청": "S2 승인 즉시 지급요청",
    "S3 재제출 지연 최대 1일": "S3 재제출 1일 이내",
    "S1+S2+S3 함께": "S1+S2+S3 모두",
}
