# Public Web App

AWS ECS Fargate에 배포되는 외부 공개용 Flask 웹 애플리케이션이다.

이 애플리케이션은 하이브리드 운영 플랫폼에서 외부 사용자 요청을 처리하는 Public Service 역할을 담당한다. 또한 장애 테스트 endpoint와 온프레미스 Internal Ops API 연계 endpoint를 제공해 CloudWatch 기반 장애 감지, EventBridge/Lambda 이벤트 처리, S3 장애 이벤트 저장, LLM 기반 장애 요약 자동화 흐름을 검증하는 데 사용된다.

---

## 1. 역할

Public Web App은 다음 역할을 수행한다.

- AWS ECS Fargate에서 실행되는 공개 웹 서비스
- ALB를 통한 외부 요청 처리
- `/health` 기반 ALB Target Group 헬스체크
- `/error`, `/slow`, `/stress` 기반 장애 시나리오 제공
- `/status/internal` 기반 온프레미스 Internal Ops API 상태 조회
- CloudWatch Logs를 통한 애플리케이션 로그 수집 대상
- CloudWatch Alarm 테스트 대상

---

## 2. 기술 스택

| Category | Technology |
|---|---|
| Language | Python |
| Framework | Flask |
| WSGI Server | Gunicorn |
| Container | Docker |
| Runtime | AWS ECS Fargate |
| Registry | Amazon ECR |
| Logs | CloudWatch Logs |

---

## 3. 파일 구성

```text
public-web/
├── app.py
├── requirements.txt
├── Dockerfile
└── README.md
```

| File | Description |
|---|---|
| `app.py` | Flask 애플리케이션 코드 |
| `requirements.txt` | Python 패키지 목록 |
| `Dockerfile` | ECS 배포용 Docker 이미지 빌드 파일 |
| `README.md` | Public Web App 설명 문서 |

---

## 4. 환경변수

| Name | Default | Description |
|---|---|---|
| `SERVICE_NAME` | `public-web-app` | 서비스 이름 |
| `APP_VERSION` | `v0.1.0` 또는 `v0.2.0` | 애플리케이션 버전 |
| `INTERNAL_OPS_API_URL` | `not-configured` | 온프레미스 Internal Ops API 접근 URL |
| `PYTHONUNBUFFERED` | `1` | 컨테이너 로그 출력 버퍼링 비활성화 |

`INTERNAL_OPS_API_URL`은 `/status/internal` endpoint에서 사용된다. MVP에서는 ngrok 임시 터널 URL을 사용했고, 운영 환경에서는 Site-to-Site VPN 또는 보안 터널을 통해 접근 가능한 내부 URL로 교체할 수 있다.

예시:

```text
INTERNAL_OPS_API_URL=https://example.ngrok-free.dev
```

---

## 5. Endpoint

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | 서비스 기본 정보와 endpoint 목록 반환 |
| `GET` | `/health` | 서비스 헬스체크 |
| `GET` | `/version` | 서비스 버전 정보 |
| `GET` | `/status/internal` | 온프레미스 Internal Ops API 상태 조회 |
| `GET` | `/error` | 의도적 500 에러 발생 |
| `GET` | `/slow?delay=3` | 지정 시간만큼 응답 지연 |
| `GET` | `/stress` | CPU 부하 테스트 |

---

## 6. Endpoint 상세

### 6.1 `/health`

ALB Target Group 헬스체크에 사용되는 endpoint다.

```bash
curl http://localhost:5000/health
```

예상 응답:

```json
{
  "status": "ok",
  "service": "public-web-app",
  "version": "v0.2.0",
  "timestamp": "2026-05-08T00:00:00Z"
}
```

---

### 6.2 `/version`

현재 애플리케이션 버전을 반환한다.

```bash
curl http://localhost:5000/version
```

예상 응답:

```json
{
  "service": "public-web-app",
  "version": "v0.2.0"
}
```

---

### 6.3 `/status/internal`

온프레미스 k3s 클러스터에 배포된 Internal Ops API의 `/ops/health` endpoint를 호출한다.

```bash
curl http://localhost:5000/status/internal
```

정상 연결 시 응답 예시:

```json
{
  "service": "public-web-app",
  "status": "connected",
  "internal_ops_api_url": "https://example.ngrok-free.dev",
  "internal_status_code": 200,
  "internal_response": {
    "service": "internal-ops-api",
    "status": "ok",
    "version": "v0.1.0"
  }
}
```

연결 실패 시 응답 예시:

```json
{
  "service": "public-web-app",
  "status": "internal_api_error",
  "internal_ops_api_url": "https://example.ngrok-free.dev",
  "error": "..."
}
```

이 실패 로그는 CloudWatch Logs에 `Internal Ops API call failed` 메시지로 기록된다. 해당 로그는 CloudWatch Logs Metric Filter를 통해 custom metric으로 변환되고, Internal Ops API 연결 실패 Alarm을 발생시키는 데 사용된다.

---

### 6.4 `/error`

의도적으로 500 에러를 반환한다. ALB Target 5XX 장애 시나리오를 테스트하기 위한 endpoint다.

```bash
curl -i http://localhost:5000/error
```

예상 응답:

```json
{
  "status": "error",
  "message": "Intentional error for CloudWatch alarm test"
}
```

이 endpoint를 호출하면 다음 흐름을 검증할 수 있다.

```text
/error 호출
→ HTTP 500 응답
→ ALB Target 5XX metric 증가
→ CloudWatch Alarm
→ EventBridge
→ Lambda
→ S3 incidents JSON 저장
→ LLM summary Markdown 생성
```

---

### 6.5 `/slow`

응답 지연을 유도한다.

```bash
curl "http://localhost:5000/slow?delay=3"
```

예상 응답:

```json
{
  "status": "ok",
  "message": "Response delayed by 3 seconds"
}
```

ALB Target Response Time, timeout, slow request 시나리오를 실험할 때 사용할 수 있다.

---

### 6.6 `/stress`

단순 반복 연산으로 CPU 부하를 유도한다.

```bash
curl http://localhost:5000/stress
```

ECS CPU Utilization 기반 모니터링이나 부하 시나리오를 실험할 때 사용할 수 있다.

---

## 7. Local Run

로컬에서 Flask 애플리케이션을 직접 실행한다.

```bash
pip install -r requirements.txt
python app.py
```

기본 실행 주소:

```text
http://localhost:5000
```

테스트:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/version
curl http://localhost:5000/error
```

---

## 8. Docker Run

Docker 이미지를 빌드한다.

```bash
docker build -t public-web-app:v0.2.0 .
```

컨테이너 실행:

```bash
docker run -p 5000:5000 public-web-app:v0.2.0
```

환경변수를 포함해 실행:

```bash
docker run -p 5000:5000   -e SERVICE_NAME=public-web-app   -e APP_VERSION=v0.2.0   -e INTERNAL_OPS_API_URL=https://example.ngrok-free.dev   public-web-app:v0.2.0
```

테스트:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/status/internal
```

---

## 9. ECR Push

ECR Repository URI 확인:

```powershell
aws cloudformation describe-stacks `
  --stack-name hybrid-ops-ecr-dev `
  --query "Stacks[0].Outputs"
```

Docker tag:

```powershell
docker tag public-web-app:v0.2.0 `
  <ECR_REPOSITORY_URI>:v0.2.0
```

Docker push:

```powershell
docker push <ECR_REPOSITORY_URI>:v0.2.0
```

---

## 10. ECS 배포

ECS 배포는 루트의 CloudFormation 템플릿에서 수행한다.

```text
infra/aws/01-ecs-public-web.yaml
```

배포 또는 업데이트 예시:

```powershell
aws cloudformation update-stack `
  --stack-name hybrid-ops-public-web-dev `
  --template-body file://infra/aws/01-ecs-public-web.yaml `
  --parameters `
    ParameterKey=ImageUri,ParameterValue=<ECR_REPOSITORY_URI>:v0.2.0 `
    ParameterKey=InternalOpsApiUrl,ParameterValue=<NGROK_URL> `
  --capabilities CAPABILITY_NAMED_IAM
```

배포 후 ALB URL로 확인한다.

```powershell
curl.exe http://<ALB_DNS>/health
curl.exe http://<ALB_DNS>/status/internal
```

---

## 11. 장애 시나리오

### 11.1 Public Web App 5XX 장애

```powershell
curl.exe -i http://<ALB_DNS>/error
```

검증 흐름:

```text
/error
→ ALB Target 5XX
→ CloudWatch Alarm
→ EventBridge
→ Lambda A
→ S3 incidents JSON
→ Lambda B
→ OpenAI API
→ S3 summaries Markdown
```

---

### 11.2 하이브리드 연결 장애

ngrok 또는 Kubernetes port-forward를 중단한 뒤 호출한다.

```powershell
curl.exe -i http://<ALB_DNS>/status/internal
```

검증 흐름:

```text
/status/internal
→ Internal Ops API 호출 실패
→ CloudWatch Logs에 "Internal Ops API call failed" 기록
→ CloudWatch Logs Metric Filter
→ CloudWatch Alarm
→ EventBridge
→ Lambda A
→ S3 incidents JSON
→ Lambda B
→ OpenAI API
→ S3 summaries Markdown
```

---

## 12. 로그

ECS 컨테이너 로그는 CloudWatch Logs에 저장된다.

```text
/ecs/hybrid-ops-dev-public-web-app
```

확인 명령:

```powershell
aws logs describe-log-streams `
  --log-group-name "/ecs/hybrid-ops-dev-public-web-app" `
  --order-by LastEventTime `
  --descending `
  --max-items 5
```

특정 로그 스트림 조회:

```powershell
aws logs get-log-events `
  --log-group-name "/ecs/hybrid-ops-dev-public-web-app" `
  --log-stream-name "<LOG_STREAM_NAME>" `
  --limit 30
```

주요 로그 메시지:

```text
Intentional error triggered from /error endpoint
Internal Ops API call failed
```

---

## 13. 설계 포인트

### 13.1 `/health` 분리

`/health`는 ALB Target Group 헬스체크 전용 endpoint로 사용한다. 이 endpoint는 외부 의존성 없이 애플리케이션 자체의 생존 여부만 반환한다.

### 13.2 `/status/internal` 분리

`/status/internal`은 온프레미스 Internal Ops API와의 연결 상태를 확인하는 endpoint다. 외부 의존성 실패를 별도로 관측하기 위해 `/health`와 분리했다.

### 13.3 장애 테스트 endpoint 제공

`/error`, `/slow`, `/stress` endpoint를 통해 에러, 지연, 부하 상황을 의도적으로 발생시킬 수 있다. 이를 통해 CloudWatch와 장애 자동화 파이프라인을 반복적으로 테스트할 수 있다.

### 13.4 환경변수 기반 하이브리드 연결

온프레미스 API 주소는 코드에 고정하지 않고 `INTERNAL_OPS_API_URL` 환경변수로 분리했다. MVP에서는 ngrok URL을 사용하고, 운영 환경에서는 Site-to-Site VPN을 통해 접근 가능한 내부 주소로 교체할 수 있다.

---

## 14. Troubleshooting

### Dockerfile을 찾지 못하는 경우

파일명이 `Dockerfile.txt`로 되어 있으면 Docker가 인식하지 못한다.

```powershell
Rename-Item Dockerfile.txt Dockerfile
```

### `public-web-app:v0.2.0` 이미지가 없다는 경우

먼저 이미지를 빌드해야 한다.

```powershell
docker build -t public-web-app:v0.2.0 .
```

### `/status/internal`이 502를 반환하는 경우

확인할 항목:

```text
- ngrok 실행 여부
- port-forward 실행 여부
- INTERNAL_OPS_API_URL 값
- Internal Ops API Pod 상태
- /ops/health 직접 호출 가능 여부
```

### ngrok HTTPS curl 오류

Windows curl에서 인증서 revocation check 오류가 날 수 있다.

```powershell
curl.exe --ssl-no-revoke https://<NGROK_URL>/ops/health
```

---

## 15. Summary

Public Web App은 이 프로젝트에서 AWS 공개 서비스 역할을 담당한다.  
단순한 Flask 앱이 아니라, 하이브리드 연결 검증과 장애 자동화 시나리오의 중심 역할을 한다.

이 앱을 통해 다음을 검증했다.

```text
AWS ECS 공개 서비스 배포
→ ALB 기반 외부 접근
→ 온프레미스 Internal Ops API 원격 조회
→ Public Web App 5XX 장애 재현
→ 하이브리드 연결 장애 재현
→ CloudWatch 기반 관측 및 장애 자동화 연계
```
