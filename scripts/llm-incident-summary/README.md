# Incident Summary Script

S3에 저장된 장애 이벤트 JSON을 기반으로 운영자용 장애 요약 보고서를 생성하는 스크립트/요약 모듈이다.

이 디렉터리는 두 가지 목적을 가진다.

```text
1. 로컬 테스트용 장애 요약 스크립트
2. AWS Lambda + OpenAI API 기반 자동 장애 요약 흐름의 로직 정리
```

전체 프로젝트에서는 CloudWatch Alarm, EventBridge, Lambda A를 통해 S3 `incidents/` 경로에 장애 이벤트 JSON을 저장하고, 이후 S3 ObjectCreated 이벤트를 트리거로 Lambda B가 실행되어 LLM 기반 장애 요약 Markdown 파일을 생성한다.

---

## 1. 역할

이 스크립트의 역할은 장애 이벤트 JSON을 사람이 읽기 쉬운 보고서 형태로 변환하는 것이다.

```text
S3 incidents/*.json
  |
  v
장애 이벤트 핵심 정보 추출
  |
  v
장애 요약 / 원인 후보 / 점검 순서 / 대응 절차 생성
  |
  v
incident_summary.txt 또는 incident_summary_llm.md 생성
```

---

## 2. Directory Structure

```text
scripts/
└── llm-incident-summary/
    ├── summarize_incident.py
    ├── summarize_incident_with_llm.py
    ├── sample_incident.json
    ├── requirements.txt
    ├── output/
    │   ├── incident_summary.txt
    │   └── incident_summary_llm.md
    └── README.md
```

파일 역할은 다음과 같다.

| File | Description |
|---|---|
| `sample_incident.json` | S3에서 내려받은 장애 이벤트 JSON 샘플 |
| `summarize_incident.py` | LLM 없이 정적 템플릿 기반으로 장애 요약 텍스트 생성 |
| `summarize_incident_with_llm.py` | OpenAI API를 호출해 LLM 기반 Markdown 요약 생성 |
| `requirements.txt` | OpenAI SDK 등 Python dependency |
| `output/` | 생성된 장애 요약 결과 파일 저장 경로 |

---

## 3. Input Format

입력 파일은 Lambda A가 S3에 저장한 장애 이벤트 JSON이다.

예시 경로:

```text
s3://<INCIDENT_BUCKET_NAME>/incidents/YYYY/MM/DD/<timestamp>-<alarm-name>.json
```

로컬 테스트를 위해 이 파일을 다음 위치로 내려받아 사용한다.

```text
scripts/llm-incident-summary/sample_incident.json
```

장애 이벤트 JSON에는 다음과 같은 정보가 포함된다.

```json
{
  "project": "hybrid-ops",
  "environment": "dev",
  "received_at": "2026-05-08T00:00:00Z",
  "source": "aws.cloudwatch",
  "detail_type": "CloudWatch Alarm State Change",
  "alarm_name": "hybrid-ops-dev-alb-target-5xx-alarm",
  "new_state": "ALARM",
  "region": "ap-northeast-2",
  "account": "123456789012",
  "raw_event": {
    "detail": {
      "state": {
        "value": "ALARM",
        "reason": "..."
      }
    }
  }
}
```

---

## 4. Output Format

요약 결과는 Markdown 또는 텍스트 파일로 생성된다.

```text
output/incident_summary.txt
output/incident_summary_llm.md
```

LLM 기반 요약 파일의 기본 구조는 다음과 같다.

```markdown
# LLM Incident Summary

## 1. Incident Overview
## 2. Detection Evidence
## 3. Estimated Impact
## 4. Possible Causes
## 5. First Response Checklist
## 6. Draft Response Procedure
## 7. Draft Incident Report
## 8. Prevention and Improvement Items
```

---

## 5. Local Template Summary

`summary_incident.py`는 OpenAI API를 사용하지 않고, JSON 필드를 기반으로 정해진 템플릿의 장애 보고 초안을 생성한다.

### 5.1 실행 방법

```bash
python summarize_incident.py
```

프로젝트 루트에서 실행할 경우:

```powershell
python scripts\llm-incident-summary\summarize_incident.py
```

### 5.2 출력 파일

```text
scripts/llm-incident-summary/output/incident_summary.txt
```

### 5.3 사용 목적

이 스크립트는 LLM API 없이도 장애 요약 형식을 먼저 검증하기 위한 용도로 사용한다.

```text
S3 JSON
→ 필드 추출
→ 정적 템플릿 적용
→ 장애 보고 초안 생성
```

---

## 6. LLM-based Summary

`summarize_incident_with_llm.py`는 장애 이벤트 JSON을 읽고 OpenAI API를 호출해 Markdown 형식의 장애 요약 보고서를 생성한다.

### 6.1 Dependency 설치

```bash
pip install -r requirements.txt
```

또는 프로젝트 루트에서:

```powershell
pip install -r scripts\llm-incident-summary\requirements.txt
```

`requirements.txt` 예시:

```text
openai>=1.0.0
```

### 6.2 OpenAI API Key 설정

PowerShell에서 임시 환경변수로 설정한다.

```powershell
$env:OPENAI_API_KEY="sk-..."
```

확인:

```powershell
echo $env:OPENAI_API_KEY
```

API Key는 절대 GitHub에 커밋하지 않는다.

### 6.3 실행 방법

```bash
python summarize_incident_with_llm.py
```

프로젝트 루트에서 실행할 경우:

```powershell
python scripts\llm-incident-summary\summarize_incident_with_llm.py
```

### 6.4 출력 파일

```text
scripts/llm-incident-summary/output/incident_summary_llm.md
```

---

## 7. AWS Lambda 기반 자동 요약 흐름

로컬 스크립트와 별도로, AWS에서는 Lambda B가 같은 역할을 수행한다.

전체 흐름은 다음과 같다.

```text
CloudWatch Alarm
  |
  v
EventBridge Rule
  |
  v
Lambda A: Incident Event Handler
  |
  v
S3 incidents/*.json
  |
  v
S3 ObjectCreated Trigger
  |
  v
Lambda B: Incident Summary Handler
  |
  v
OpenAI API
  |
  v
S3 summaries/*.md
```

Lambda B는 S3 `incidents/` prefix에 JSON 파일이 생성될 때 실행된다.

```text
Input:  s3://<bucket>/incidents/YYYY/MM/DD/*.json
Output: s3://<bucket>/summaries/YYYY/MM/DD/*.md
```

입력과 출력 prefix를 분리해 S3 trigger loop를 방지한다.

---

## 8. Lambda B 처리 로직

Lambda B의 처리 흐름은 다음과 같다.

```text
1. S3 ObjectCreated 이벤트 수신
2. bucket name과 object key 추출
3. incidents/*.json 파일인지 확인
4. S3에서 JSON 파일 읽기
5. 장애 이벤트 핵심 필드 추출
6. OpenAI API 호출용 prompt 구성
7. OpenAI API 호출
8. Markdown 요약 결과 생성
9. summaries/*.md 경로로 S3 저장
```

---

## 9. Prompt 설계

LLM에게 전달하는 prompt는 다음 원칙을 따른다.

```text
- JSON에서 확인 가능한 사실과 추정 내용을 구분
- 원인 후보를 단정하지 않고 가능성으로 표현
- 실제 조치 완료 여부를 단정하지 않음
- 운영자가 바로 확인할 수 있는 점검 순서 포함
- 포트폴리오와 운영 문서에 넣을 수 있는 Markdown 형식 사용
```

LLM 출력 형식:

```markdown
# LLM Incident Summary

## 1. Incident Overview
## 2. Detection Evidence
## 3. Estimated Impact
## 4. Possible Causes
## 5. First Response Checklist
## 6. Draft Response Procedure
## 7. Draft Incident Report
## 8. Prevention and Improvement Items
```

---

## 10. Supported Incident Types

현재 요약 대상은 두 가지다.

### 10.1 Public Web App 5XX Incident

Public Web App의 `/error` endpoint를 호출해 ALB Target 5XX metric이 증가한 경우다.

```text
/error
→ HTTP 500
→ ALB Target 5XX Alarm
→ S3 incidents JSON
→ LLM Summary
```

### 10.2 Hybrid Connectivity Failure

AWS ECS Public Web App이 온프레미스 Internal Ops API 호출에 실패한 경우다.

```text
ngrok 또는 port-forward 중단
→ /status/internal 502
→ CloudWatch Logs: Internal Ops API call failed
→ Metric Filter
→ CloudWatch Alarm
→ S3 incidents JSON
→ LLM Summary
```

---

## 11. S3 JSON 내려받기

S3에 저장된 incident JSON 파일을 로컬로 내려받는다.

```powershell
aws s3 ls s3://<INCIDENT_BUCKET_NAME>/incidents/ --recursive
```

예시:

```powershell
aws s3 cp `
  s3://<INCIDENT_BUCKET_NAME>/incidents/2026/05/08/example.json `
  scripts/llm-incident-summary/sample_incident.json
```

---

## 12. S3 Summary 확인

Lambda B가 정상 실행되면 `summaries/` prefix 아래에 Markdown 파일이 생성된다.

```powershell
aws s3 ls s3://<INCIDENT_BUCKET_NAME>/summaries/ --recursive
```

Markdown 파일 다운로드:

```powershell
aws s3 cp `
  s3://<INCIDENT_BUCKET_NAME>/summaries/2026/05/08/example.md `
  scripts/llm-incident-summary/output/incident_summary_llm_from_s3.md
```

---

## 13. Security Notes

이 기능은 OpenAI API Key를 사용하므로 보안 처리가 중요하다.

- API Key를 코드에 하드코딩하지 않는다.
- API Key를 GitHub에 커밋하지 않는다.
- 로컬에서는 환경변수로 관리한다.
- Lambda에서는 환경변수 또는 Secrets Manager를 사용한다.
- 캡처 화면에 API Key 값이 노출되지 않도록 주의한다.

현재 MVP에서는 Lambda 환경변수 `OPENAI_API_KEY`를 사용했다.

운영 환경에서는 AWS Secrets Manager를 사용하는 방식이 더 적절하다.

---

## 14. Troubleshooting

### 14.1 `OPENAI_API_KEY`가 없다는 오류

환경변수가 설정되지 않은 상태다.

로컬에서는 다음 명령으로 설정한다.

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Lambda에서는 콘솔에서 환경변수를 추가한다.

```text
Lambda
→ hybrid-ops-dev-incident-summary-handler
→ Configuration
→ Environment variables
→ OPENAI_API_KEY 추가
```

---

### 14.2 S3에 summary 파일이 생성되지 않는 경우

확인할 항목:

```text
1. S3 Event Notification이 incidents/ prefix와 .json suffix로 설정되어 있는지 확인
2. Lambda B trigger가 S3로 연결되어 있는지 확인
3. Lambda B CloudWatch Logs 확인
4. OPENAI_API_KEY 환경변수 존재 여부 확인
5. Lambda Role에 s3:GetObject, s3:PutObject 권한이 있는지 확인
6. output prefix가 summaries/인지 확인
```

---

### 14.3 S3 Trigger가 반복 실행되는 경우

입력과 출력 prefix가 같은 경우 발생할 수 있다.

현재 설계는 다음처럼 분리한다.

```text
Input: incidents/
Output: summaries/
```

`summaries/` 파일 생성이 다시 Lambda를 호출하지 않도록 S3 Event Notification의 prefix를 반드시 `incidents/`로 제한한다.

---

### 14.4 OpenAI API 호출 실패

가능한 원인:

```text
- API Key 누락 또는 만료
- 모델명 오류
- Lambda outbound internet 접근 문제
- API 사용량/결제 제한
- 요청 timeout
```

현재 Lambda는 public network 환경에서 실행되므로 별도 VPC에 넣지 않았다.  
만약 Lambda를 private subnet에 배치한다면 NAT Gateway 또는 VPC endpoint 구성을 고려해야 한다.

---

## 15. Why Separate Template Summary and LLM Summary?

처음에는 LLM API 없이 정적 템플릿 기반 요약을 구현했다.  
그 이유는 장애 이벤트 JSON의 구조를 먼저 이해하고, 어떤 필드를 보고서에 사용할지 검증하기 위해서다.

이후 OpenAI API를 붙여 LLM 기반 요약으로 확장했다.

```text
1단계: JSON → 정적 템플릿 보고서
2단계: JSON → LLM Prompt → Markdown 보고서
3단계: S3 ObjectCreated → Lambda → OpenAI API → S3 Summary
```

이 방식은 기능을 단계적으로 검증할 수 있고, LLM API 문제가 생겨도 기본 보고서 생성 로직을 따로 유지할 수 있다는 장점이 있다.

---

## 16. Summary

이 디렉터리는 장애 이벤트 JSON을 운영자가 이해하기 쉬운 보고서로 변환하는 기능을 담당한다.

핵심 흐름은 다음과 같다.

```text
장애 이벤트 원본 JSON
→ 핵심 필드 추출
→ 원인 후보 및 점검 항목 정리
→ LLM 기반 Markdown 보고서 생성
→ S3 summaries/ 저장
```

이 기능을 통해 장애 발생 후 운영자가 CloudWatch와 S3 이벤트 원문을 직접 분석하지 않아도, 장애 개요와 대응 초안을 빠르게 확인할 수 있다.
