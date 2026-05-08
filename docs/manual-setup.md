# Manual Setup Notes

이 문서는 CloudFormation으로 자동 생성되지 않고, AWS Console에서 수동으로 설정해야 하는 항목을 정리한다.

현재 프로젝트에서 수동 설정이 필요한 항목은 다음과 같다.

```text
1. Lambda B 환경변수 OPENAI_API_KEY 설정
2. S3 Event Notification 설정
```

---

## 1. 왜 수동 설정이 필요한가?

`02-incident-automation.yaml`은 다음 리소스를 생성한다.

```text
- S3 Incident Archive Bucket
- Lambda A: incident-event-handler
- Lambda B: incident-summary-handler
- CloudWatch Alarm
- CloudWatch Logs Metric Filter
- EventBridge Rule
- IAM Role
```

다만 S3 `ObjectCreated` 이벤트를 Lambda B에 연결하는 설정은 CloudFormation에 포함하지 않았다.

이유는 S3 Bucket Notification과 Lambda Permission을 같은 CloudFormation Stack에서 구성할 경우 순환 참조 문제가 발생할 수 있기 때문이다. 따라서 이 프로젝트에서는 S3 Event Notification을 AWS Console에서 수동으로 설정했다.

---

## 2. 수동 설정 대상

### 2.1 Lambda B 환경변수

Lambda B는 S3에 저장된 incident JSON을 읽고 OpenAI API를 호출해 Markdown 요약 파일을 생성한다.

따라서 OpenAI API 호출을 위해 다음 환경변수가 필요하다.

| 환경변수 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 호출에 필요한 API Key |
| `OPENAI_MODEL` | 사용할 OpenAI 모델 이름 |
| `SUMMARY_OUTPUT_PREFIX` | 생성된 summary Markdown 파일을 저장할 S3 prefix |

예시:

```text
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
SUMMARY_OUTPUT_PREFIX=summaries/
```

`OPENAI_API_KEY`는 절대 GitHub에 커밋하지 않는다.

---

## 3. Lambda B 환경변수 설정 방법

AWS Console에서 다음 경로로 이동한다.

```text
Lambda
→ hybrid-ops-dev-incident-summary-handler
→ Configuration
→ Environment variables
→ Edit
```

다음 값을 추가하거나 확인한다.

| Key | Value |
|---|---|
| `OPENAI_API_KEY` | `sk-...` |
| `OPENAI_MODEL` | `gpt-4.1-mini` |
| `SUMMARY_OUTPUT_PREFIX` | `summaries/` |

CLI로 설정할 수도 있다.

```powershell
aws lambda update-function-configuration `
  --function-name hybrid-ops-dev-incident-summary-handler `
  --environment "Variables={OPENAI_MODEL=gpt-4.1-mini,SUMMARY_OUTPUT_PREFIX=summaries/,OPENAI_API_KEY=sk-...}"
```

주의: 위 CLI 명령은 Lambda 환경변수 전체를 덮어쓴다. 따라서 기존 환경변수를 모두 함께 넣어야 한다.

---

## 4. S3 Event Notification의 목적

S3 `incidents/` prefix에 장애 이벤트 JSON 파일이 생성되면, Lambda B가 자동 실행되어 OpenAI API를 호출하고 장애 요약 Markdown 파일을 `summaries/` prefix에 저장한다.

```text
S3 incidents/*.json
  |
  v
S3 ObjectCreated Event
  |
  v
Lambda B: hybrid-ops-dev-incident-summary-handler
  |
  v
OpenAI API
  |
  v
S3 summaries/*.md
```

---

## 5. Incident Archive Bucket 이름 확인

Incident Archive Bucket 이름은 CloudFormation Output에서 확인한다.

```powershell
aws cloudformation describe-stacks `
  --stack-name hybrid-ops-incident-automation-dev `
  --query "Stacks[0].Outputs"
```

확인할 Output:

```text
IncidentArchiveBucketName
```

예시:

```text
hybrid-ops-incident-automation-dev-incidentarchivebucket-xxxxxxxx
```

---

## 6. S3 Event Notification 설정 위치

AWS Console에서 다음 경로로 이동한다.

```text
S3
→ Incident Archive Bucket
→ Properties
→ Event notifications
→ Create event notification
```

---

## 7. S3 Event Notification 설정값

다음 값으로 설정한다.

| 항목 | 값 |
|---|---|
| Event name | `trigger-incident-summary` |
| Prefix | `incidents/` |
| Suffix | `.json` |
| Event types | `All object create events` |
| Destination | `Lambda function` |
| Lambda function | `hybrid-ops-dev-incident-summary-handler` |

---

## 8. Prefix/Suffix를 제한하는 이유

S3 Event Notification은 객체 생성 이벤트를 기준으로 Lambda를 호출한다.

이 프로젝트에서는 Lambda B가 요약 결과를 같은 S3 Bucket의 `summaries/` prefix에 저장한다. 만약 S3 Event Notification이 bucket 전체에 대해 설정되어 있으면, Lambda B가 `summaries/*.md` 파일을 생성할 때 다시 자기 자신을 호출하는 문제가 생길 수 있다.

이를 방지하기 위해 입력 prefix와 출력 prefix를 분리했다.

```text
Input:  incidents/*.json
Output: summaries/*.md
```

따라서 Event Notification은 반드시 다음 조건으로 제한한다.

```text
Prefix: incidents/
Suffix: .json
```

---

## 9. 정상 동작 확인

S3 Event Notification 설정 후, 기존 incident JSON을 새 이름으로 복사하면 Lambda B가 실행되는지 테스트할 수 있다.

먼저 incident JSON 목록을 확인한다.

```powershell
aws s3 ls s3://<INCIDENT_BUCKET_NAME>/incidents/ --recursive
```

기존 JSON 하나를 새 파일명으로 복사한다.

```powershell
aws s3 cp `
  s3://<INCIDENT_BUCKET_NAME>/incidents/YYYY/MM/DD/example.json `
  s3://<INCIDENT_BUCKET_NAME>/incidents/YYYY/MM/DD/test-s3-trigger.json
```

이후 summaries 경로를 확인한다.

```powershell
aws s3 ls s3://<INCIDENT_BUCKET_NAME>/summaries/ --recursive
```

정상이라면 다음과 같은 Markdown 파일이 생성된다.

```text
summaries/YYYY/MM/DD/test-s3-trigger.md
```

---

## 10. 실제 장애 시나리오 테스트

### 10.1 Public Web App 5XX Incident

Public Web App의 `/error` endpoint를 호출한다.

```powershell
curl.exe -i http://<ALB_DNS>/error
```

예상 흐름:

```text
/error
→ ALB Target 5XX 증가
→ CloudWatch Alarm
→ EventBridge
→ Lambda A
→ S3 incidents/*.json
→ S3 Event Notification
→ Lambda B
→ OpenAI API
→ S3 summaries/*.md
```

### 10.2 Hybrid Connectivity Failure

ngrok 또는 port-forward를 중단한 뒤 `/status/internal`을 호출한다.

```powershell
curl.exe -i http://<ALB_DNS>/status/internal
```

예상 흐름:

```text
/status/internal
→ Internal Ops API call failed 로그 기록
→ CloudWatch Logs Metric Filter
→ CloudWatch Alarm
→ EventBridge
→ Lambda A
→ S3 incidents/*.json
→ S3 Event Notification
→ Lambda B
→ OpenAI API
→ S3 summaries/*.md
```

---

## 11. 문제 발생 시 확인할 항목

summary 파일이 생성되지 않으면 다음 항목을 확인한다.

```text
1. S3 Event Notification의 Prefix가 incidents/인지 확인
2. S3 Event Notification의 Suffix가 .json인지 확인
3. Event type이 All object create events인지 확인
4. Destination Lambda가 hybrid-ops-dev-incident-summary-handler인지 확인
5. Lambda B에 OPENAI_API_KEY 환경변수가 있는지 확인
6. Lambda B IAM Role에 s3:GetObject, s3:PutObject 권한이 있는지 확인
7. Lambda B CloudWatch Logs에서 오류 확인
8. S3 summaries/ prefix에 파일이 생성되었는지 확인
```

Lambda B 로그 그룹:

```text
/aws/lambda/hybrid-ops-dev-incident-summary-handler
```

---

## 12. 관련 리소스

| 리소스 | 역할 |
|---|---|
| `IncidentArchiveBucket` | incident JSON과 summary Markdown 저장 |
| `IncidentEventHandlerFunction` | CloudWatch Alarm 이벤트를 S3 incidents JSON으로 저장 |
| `IncidentSummaryFunction` | S3 incident JSON을 읽고 LLM summary 생성 |
| `S3 Event Notification` | incidents/*.json 생성 시 Lambda B 실행 |
| `OPENAI_API_KEY` | OpenAI API 호출에 필요한 인증 정보 |

---

## 13. 재현 시 주의사항

이 설정은 CloudFormation Stack 삭제 후 다시 생성하면 사라진다.

따라서 프로젝트를 재현할 때는 `02-incident-automation.yaml` 배포 후 반드시 다음 두 가지를 다시 수행해야 한다.

```text
1. Lambda B에 OPENAI_API_KEY 환경변수 추가
2. S3 Event Notification 수동 설정
```

---

## 14. GitHub에 올리지 말아야 할 정보

다음 정보는 GitHub에 커밋하지 않는다.

```text
- OPENAI_API_KEY
- ngrok authtoken
- AWS Access Key / Secret Access Key
- 개인 AWS Account ID가 포함된 민감 캡처
- VM SSH private key
- .env 파일
```

`.gitignore`에 다음 항목을 추가하는 것을 권장한다.

```gitignore
.env
*.pem
private-reproduce-notes.md
```

---

## 15. 요약

이 프로젝트에서 GitHub와 CloudFormation만으로 자동 재현되지 않는 핵심 수동 설정은 다음 두 가지다.

```text
1. Lambda B 환경변수 OPENAI_API_KEY 설정
2. S3 Event Notification 설정
   - Prefix: incidents/
   - Suffix: .json
   - Event: All object create events
   - Destination: hybrid-ops-dev-incident-summary-handler
```

이 두 가지를 설정해야 S3에 incident JSON이 생성된 뒤 LLM 기반 summary Markdown 파일이 자동으로 생성된다.
