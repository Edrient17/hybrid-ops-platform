# Hybrid Ops Platform

온프레미스 Kubernetes와 AWS ECS를 연계한 하이브리드 웹서비스 운영 및 장애 대응 자동화 플랫폼이다.

로컬 가상화 환경에는 k3s 기반 Internal Ops Platform을 구성하고, AWS에는 ECS Fargate 기반 Public Web App을 배포했다. 또한 CloudWatch, EventBridge, Lambda, S3, OpenAI API를 연계해 장애 이벤트 수집과 LLM 기반 장애 요약 자동화 흐름을 구현했다.

---

## 1. 프로젝트 개요

이 프로젝트는 단순히 웹 애플리케이션을 배포하는 것이 아니라, 실제 운영 환경에서 필요한 장애 감지, 이벤트 처리, 로그 수집, 장애 요약, 보고 초안 생성 흐름을 직접 구현하는 것을 목표로 한다.

주요 목표는 다음과 같다.

- 온프레미스 Kubernetes 기반 내부 운영 시스템 구성
- AWS ECS Fargate 기반 외부 공개 서비스 배포
- 온프레미스와 AWS 간 임시 하이브리드 연결 검증
- CloudWatch 기반 장애 감지
- EventBridge와 Lambda 기반 이벤트 처리
- S3 기반 장애 이벤트 아카이빙
- OpenAI API 기반 장애 요약 Markdown 자동 생성
- 장애 시나리오 재현 및 관측

---

## 2. 전체 아키텍처

### 2.1 서비스 구조

```text
User
  |
  v
AWS Application Load Balancer
  |
  v
ECS Fargate Public Web App
  |
  |-- /health
  |-- /version
  |-- /error
  |-- /slow
  |-- /stress
  |
  |-- /status/internal
          |
          v
      ngrok Temporary Tunnel
          |
          v
On-Premise k3s Internal Ops API
  |
  |-- /ops/health
  |-- /ops/summary
  |-- /ops/incidents
  |-- /ops/version
```

온프레미스 k3s는 내부 운영 시스템 역할을 맡고, AWS ECS는 외부 사용자 대상 공개 서비스 역할을 맡는다. 두 환경은 MVP 단계에서 ngrok 임시 터널로 연결했고, 운영 환경에서는 Site-to-Site VPN으로 확장할 수 있는 구조로 설계했다.

### 2.2 장애 자동화 구조

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

장애 이벤트는 먼저 원본 JSON 형태로 S3에 저장된다. 이후 S3 ObjectCreated 이벤트를 트리거로 LLM 요약 Lambda가 실행되고, OpenAI API를 호출해 Markdown 형식의 장애 요약 보고서를 생성한다.

---

## 3. 기술 스택

### 3.1 On-Premise

| Category | Technology |
|---|---|
| Virtualization | VMware Workstation Pro |
| OS | Ubuntu Server |
| Kubernetes | k3s |
| Ingress | Traefik |
| Application | Python Flask |
| Monitoring | Prometheus, Grafana, Node Exporter |
| Logging | Loki, Promtail |

### 3.2 AWS

| Category | Technology |
|---|---|
| Container Registry | Amazon ECR |
| Compute | Amazon ECS Fargate |
| Load Balancing | Application Load Balancer |
| Monitoring | CloudWatch Metrics, CloudWatch Logs, CloudWatch Alarm |
| Event Processing | EventBridge, Lambda |
| Storage | Amazon S3 |
| IAM | IAM Role, IAM Policy |
| IaC | CloudFormation |

### 3.3 Automation / AI

| Category | Technology |
|---|---|
| Container | Docker |
| API | OpenAI API |
| Summary | LLM-based Incident Summary |
| Script | Python |

---

## 4. Repository Structure

```text
hybrid-ops-platform/
├── app/
│   └── public-web/
│       ├── app.py
│       ├── requirements.txt
│       ├── Dockerfile
│       └── README.md
│
├── infra/
│   └── aws/
│       ├── 00-ecr.yaml
│       ├── 01-ecs-public-web.yaml
│       └── 02-incident-automation.yaml
│
├── scripts/
│   └── llm-incident-summary/
│       ├── summarize_incident.py
│       ├── sample_incident.json
│       ├── output/
│       └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── hybrid-connectivity.md
│   ├── incident-scenarios.md
│   ├── runbook.md
│   ├── troubleshooting.md
│   └── screenshots/
│
└── README.md
```

---

## 5. On-Premise Kubernetes 구성

온프레미스 영역은 VMware 기반 Ubuntu Server VM 3대로 구성했다.

```text
k3s-control-01
k3s-worker-01
k3s-worker-02
```

k3s 클러스터 위에는 내부 운영용 API와 모니터링/로그 수집 스택을 배포했다.

```text
Kubernetes Cluster
├── app namespace
│   └── Internal Ops API
│
├── monitoring namespace
│   ├── Prometheus
│   ├── Grafana
│   ├── Alertmanager
│   └── Node Exporter
│
└── logging namespace
    ├── Loki
    └── Promtail
```

### 5.1 Internal Ops API

Internal Ops API는 온프레미스 Kubernetes 클러스터 내부에 배포된 운영자용 API다.

| Endpoint | Description |
|---|---|
| `/ops/health` | 서비스 상태 확인 |
| `/ops/summary` | 운영 상태 요약 |
| `/ops/incidents` | 장애 이력 조회 |
| `/ops/version` | 버전 정보 확인 |

### 5.2 On-Premise 장애 시나리오

Internal Ops API Pod를 강제로 삭제해 Kubernetes Deployment의 self-healing 동작을 확인했다.

```text
Pod 삭제
→ Deployment Controller가 신규 Pod 생성
→ replicas=2 상태 복구
→ Service와 Ingress를 통한 API 응답 유지
```

이를 통해 Pod 단위 장애가 발생해도 Kubernetes가 desired state를 복구하는 흐름을 검증했다.

---

## 6. AWS ECS Public Web App 구성

AWS에는 외부 공개용 Public Web App을 ECS Fargate로 배포했다.

Public Web App은 Flask 기반으로 작성했고, Docker 이미지로 빌드한 뒤 ECR에 push했다. 이후 CloudFormation으로 VPC, ALB, ECS Cluster, ECS Service, Task Definition, CloudWatch Log Group을 구성했다.

### 6.1 Public Web App Endpoints

| Endpoint | Description |
|---|---|
| `/` | 서비스 기본 정보 |
| `/health` | ALB/ECS 헬스체크 |
| `/version` | 애플리케이션 버전 정보 |
| `/status/internal` | 온프레미스 Internal Ops API 연계 상태 확인 |
| `/error` | 500 에러 장애 테스트 |
| `/slow` | 지연 응답 테스트 |
| `/stress` | CPU 부하 테스트 |

### 6.2 AWS 리소스

CloudFormation으로 다음 리소스를 구성했다.

```text
ECR Repository
VPC
Public Subnet
Internet Gateway
Route Table
Security Group
Application Load Balancer
Target Group
ECS Cluster
ECS Task Definition
ECS Service
CloudWatch Log Group
IAM Role
```

---

## 7. Hybrid Connectivity

온프레미스와 AWS는 MVP 단계에서 ngrok 임시 터널로 연결했다.

AWS ECS Public Web App의 `INTERNAL_OPS_API_URL` 환경변수에 ngrok URL을 설정하고, `/status/internal` endpoint에서 온프레미스 Internal Ops API의 `/ops/health` endpoint를 호출하도록 구성했다.

```text
AWS ECS Public Web App
  |
  v
/status/internal
  |
  v
ngrok temporary tunnel
  |
  v
On-Premise k3s Internal Ops API
```

### 7.1 정상 연결 결과

AWS ALB를 통해 `/status/internal`을 호출하면 온프레미스 Internal Ops API의 상태 응답이 반환된다.

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

이를 통해 AWS 공개 서비스가 온프레미스 내부 운영 API 상태를 원격으로 조회할 수 있음을 검증했다.

### 7.2 운영 환경 확장안

ngrok은 MVP 검증용 임시 터널이다. 운영 환경에서는 다음 구조로 확장할 수 있다.

```text
AWS VPC
  |
  v
Virtual Private Gateway
  |
  v
Site-to-Site VPN
  |
  v
Customer Gateway
  |
  v
On-Premise Network
  |
  v
k3s Internal Ops API
```

운영 환경에서는 Site-to-Site VPN을 통해 AWS VPC와 온프레미스 네트워크를 사설망으로 연결하고, `INTERNAL_OPS_API_URL` 값을 내부 DNS 또는 사설 IP 기반 주소로 교체할 수 있다.

---

## 8. Incident Automation

이 프로젝트에서는 두 가지 장애 시나리오를 자동화 대상으로 삼았다.

### 8.1 Scenario 1: Public Web App 5XX Error

Public Web App의 `/error` endpoint를 호출해 의도적으로 500 에러를 발생시켰다.

```text
/error 호출
  |
  v
Flask App 500 응답
  |
  v
ALB Target 5XX metric 증가
  |
  v
CloudWatch Alarm
  |
  v
EventBridge Rule
  |
  v
Lambda A
  |
  v
S3 incidents/*.json
  |
  v
Lambda B + OpenAI API
  |
  v
S3 summaries/*.md
```

이 시나리오는 AWS 공개 서비스 자체의 장애를 감지하고 처리하는 흐름을 검증하기 위한 것이다.

### 8.2 Scenario 2: Hybrid Connectivity Failure

ngrok 또는 Kubernetes port-forward를 중단해 AWS ECS에서 온프레미스 Internal Ops API를 호출할 수 없는 상황을 만들었다.

```text
ngrok 또는 port-forward 중단
  |
  v
/status/internal 호출
  |
  v
Internal Ops API call failed 로그 기록
  |
  v
CloudWatch Logs Metric Filter
  |
  v
CloudWatch Alarm
  |
  v
EventBridge Rule
  |
  v
Lambda A
  |
  v
S3 incidents/*.json
  |
  v
Lambda B + OpenAI API
  |
  v
S3 summaries/*.md
```

이 시나리오는 하이브리드 환경에서 클라우드 공개 서비스가 온프레미스 내부 API에 의존할 때, 연결 장애가 어떻게 감지되고 기록되는지 검증하기 위한 것이다.

---

## 9. Lambda Functions

### 9.1 Lambda A: Incident Event Handler

CloudWatch Alarm 상태 변경 이벤트를 EventBridge로 전달받고, 이벤트 원본을 S3에 JSON 형식으로 저장한다.

역할:

```text
CloudWatch Alarm Event 수신
→ 이벤트 메타데이터 정리
→ S3 incidents/YYYY/MM/DD/*.json 저장
```

이 Lambda는 외부 API에 의존하지 않고 빠르게 장애 원본 이벤트를 보존하는 역할만 수행한다.

### 9.2 Lambda B: Incident Summary Handler

S3 `incidents/` prefix에 JSON 파일이 생성되면 S3 ObjectCreated 이벤트로 실행된다. 저장된 장애 이벤트 JSON을 읽고 OpenAI API를 호출해 Markdown 형식의 장애 요약 보고서를 생성한다.

역할:

```text
S3 incidents/*.json 읽기
→ 장애 이벤트 핵심 정보 추출
→ OpenAI API 호출
→ S3 summaries/YYYY/MM/DD/*.md 저장
```

Lambda A와 Lambda B를 분리한 이유는 장애 이벤트 원본 저장과 LLM 기반 후처리 책임을 분리하기 위해서다. OpenAI API 지연이나 실패가 발생해도 원본 장애 이벤트는 S3에 먼저 보존되도록 설계했다.

---

## 10. LLM-based Incident Summary

S3에 저장된 장애 이벤트 JSON을 기반으로 OpenAI API를 호출해 Markdown 형식의 장애 요약 보고서를 생성한다.

생성되는 보고서 구조는 다음과 같다.

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

이 기능을 통해 장애 발생 후 운영자가 바로 확인할 수 있는 요약, 원인 후보, 점검 순서, 대응 절차 초안을 자동으로 생성할 수 있다.

---

## 11. CloudFormation Stacks

AWS 리소스는 CloudFormation으로 관리한다.

### 11.1 00-ecr.yaml

ECR Repository를 생성한다.

```text
hybrid-ops-dev-public-web-app
```

### 11.2 01-ecs-public-web.yaml

Public Web App 실행 환경을 구성한다.

```text
VPC
Public Subnet
Internet Gateway
ALB
Target Group
ECS Cluster
ECS Service
Task Definition
CloudWatch Log Group
IAM Role
```

### 11.3 02-incident-automation.yaml

장애 자동화 리소스를 구성한다.

```text
S3 Incident Archive Bucket
CloudWatch Alarm
CloudWatch Logs Metric Filter
EventBridge Rule
Lambda A
Lambda B
IAM Role
```

---

## 12. Deployment Flow

### 12.1 ECR 생성

```powershell
aws cloudformation create-stack `
  --stack-name hybrid-ops-ecr-dev `
  --template-body file://infra/aws/00-ecr.yaml
```

### 12.2 Docker 이미지 빌드 및 Push

```powershell
docker build -t public-web-app:v0.2.0 .

docker tag public-web-app:v0.2.0 `
  <ECR_REPOSITORY_URI>:v0.2.0

docker push <ECR_REPOSITORY_URI>:v0.2.0
```

### 12.3 ECS Public Web App 배포

```powershell
aws cloudformation create-stack `
  --stack-name hybrid-ops-public-web-dev `
  --template-body file://infra/aws/01-ecs-public-web.yaml `
  --parameters `
    ParameterKey=ImageUri,ParameterValue=<ECR_REPOSITORY_URI>:v0.2.0 `
    ParameterKey=InternalOpsApiUrl,ParameterValue=<NGROK_URL> `
  --capabilities CAPABILITY_NAMED_IAM
```

### 12.4 장애 자동화 스택 배포

```powershell
aws cloudformation create-stack `
  --stack-name hybrid-ops-incident-automation-dev `
  --template-body file://infra/aws/02-incident-automation.yaml `
  --parameters `
    ParameterKey=AlbFullName,ParameterValue=<ALB_FULL_NAME> `
    ParameterKey=TargetGroupFullName,ParameterValue=<TARGET_GROUP_FULL_NAME> `
    ParameterKey=PublicWebLogGroupName,ParameterValue=/ecs/hybrid-ops-dev-public-web-app `
  --capabilities CAPABILITY_NAMED_IAM
```

---

## 13. Test Scenarios

### 13.1 Public Web App Health Check

```powershell
curl.exe http://<ALB_DNS>/health
```

예상 결과:

```json
{
  "service": "public-web-app",
  "status": "ok",
  "version": "v0.2.0"
}
```

### 13.2 Hybrid Connectivity Check

```powershell
curl.exe http://<ALB_DNS>/status/internal
```

예상 결과:

```json
{
  "service": "public-web-app",
  "status": "connected",
  "internal_status_code": 200,
  "internal_response": {
    "service": "internal-ops-api",
    "status": "ok"
  }
}
```

### 13.3 Public Web App 5XX Incident

```powershell
curl.exe -i http://<ALB_DNS>/error
```

예상 흐름:

```text
HTTP 500
→ ALB Target 5XX Alarm
→ EventBridge
→ Lambda A
→ S3 incidents JSON
→ Lambda B
→ S3 summaries Markdown
```

### 13.4 Hybrid Connectivity Failure

ngrok 또는 port-forward를 중단한 뒤 다음 명령을 실행한다.

```powershell
curl.exe -i http://<ALB_DNS>/status/internal
```

예상 흐름:

```text
HTTP 502
→ CloudWatch Logs: Internal Ops API call failed
→ Metric Filter
→ CloudWatch Alarm
→ EventBridge
→ Lambda A
→ S3 incidents JSON
→ Lambda B
→ S3 summaries Markdown
```

---

## 14. Results

구현 결과 다음 흐름을 검증했다.

- AWS ALB를 통한 Public Web App 접근
- ECS Fargate 기반 컨테이너 서비스 운영
- ECR 기반 이미지 배포
- CloudWatch Logs 기반 애플리케이션 로그 수집
- ALB Target 5XX 기반 장애 감지
- CloudWatch Logs Metric Filter 기반 하이브리드 연결 장애 감지
- EventBridge 기반 Alarm state change 이벤트 처리
- Lambda 기반 장애 이벤트 S3 저장
- S3 ObjectCreated 기반 LLM 요약 Lambda 실행
- OpenAI API 기반 장애 요약 Markdown 생성
- ngrok 기반 온프레미스-AWS 임시 연결 검증

---

## 15. Troubleshooting Notes

### 15.1 Dockerfile 인식 오류

`Dockerfile.txt`로 저장되어 있으면 Docker가 파일을 찾지 못한다.

```powershell
Rename-Item Dockerfile.txt Dockerfile
```

### 15.2 ECS Service 생성 지연

초기 테스트에서 `nginx:latest` 이미지를 사용하면 컨테이너 포트와 ALB health check path가 맞지 않아 ECS Service가 안정화되지 않을 수 있다.  
이 문제를 해결하기 위해 ECR을 먼저 만들고, 실제 Flask 이미지를 push한 뒤 ECS 스택을 생성하는 방식으로 변경했다.

### 15.3 CloudWatch Alarm이 OK로 남는 문제

ALB 5XX 테스트에서는 `HTTPCode_ELB_5XX_Count`가 아니라 `HTTPCode_Target_5XX_Count`를 사용해야 한다. `/error`는 ALB 자체 오류가 아니라 Target인 Flask 앱이 반환한 500 응답이기 때문이다.

### 15.4 S3 Trigger Loop 방지

S3 ObjectCreated 이벤트로 Lambda B를 실행할 때 입력과 출력 prefix를 분리했다.

```text
Input: incidents/
Output: summaries/
```

이를 통해 summary 파일이 생성될 때 다시 Lambda가 호출되는 루프를 방지했다.

### 15.5 Lambda A와 Lambda B 분리 이유

장애 이벤트 원본 저장은 반드시 성공해야 하는 핵심 경로이고, LLM 요약은 외부 API에 의존하는 후처리 단계다.  
따라서 원본 이벤트 저장과 LLM 요약 생성을 분리해 안정성과 재처리 가능성을 높였다.

---

## 16. Security Considerations

이 프로젝트는 실습 및 포트폴리오 목적의 MVP이므로 다음 사항을 고려했다.

- AWS IAM Role은 Lambda와 ECS Task 실행에 필요한 최소 범위로 분리
- S3 Bucket Public Access 차단
- S3 서버 측 암호화 적용
- OpenAI API Key는 코드에 하드코딩하지 않고 Lambda 환경변수로 관리
- Internal Ops API는 운영 환경에서 직접 공개하지 않고 VPN 또는 보안 터널 사용 필요
- ngrok은 MVP 검증용 임시 연결이며 운영 환경에서는 Site-to-Site VPN 또는 Zero Trust 기반 터널로 대체 필요

---

## 17. Future Improvements

향후 개선할 수 있는 항목은 다음과 같다.

- AWS Site-to-Site VPN 기반 정식 하이브리드 네트워크 구성
- Route 53과 HTTPS 적용
- Discord 또는 Slack 알림 연동
- ECS Auto Scaling 구성
- CloudWatch Dashboard 구성
- Grafana Dashboard 커스터마이징
- Lambda에서 Secrets Manager를 사용해 OpenAI API Key 관리
- S3에 저장된 incident와 summary를 HTML 리포트로 자동 변환
- GitHub Actions 기반 CI/CD 자동화
- Terraform 또는 CDK 기반 IaC 확장

---

## 18. Project Summary

이 프로젝트를 통해 온프레미스 Kubernetes와 AWS ECS를 역할 기반으로 분리하고, 두 환경을 임시 터널로 연결해 하이브리드 운영 구조를 검증했다.

또한 장애를 단순히 발생시키는 데 그치지 않고, CloudWatch Alarm, EventBridge, Lambda, S3, OpenAI API를 연계해 장애 이벤트 수집과 LLM 기반 보고 초안 생성까지 이어지는 운영 자동화 흐름을 구현했다.

핵심은 다음과 같다.

```text
서비스 배포
→ 모니터링
→ 장애 감지
→ 이벤트 처리
→ 원본 보존
→ LLM 요약
→ 보고 초안 생성
```

이를 통해 단순한 클라우드 배포 프로젝트가 아니라, 실제 운영 관점에서 장애를 탐지하고 원인을 추적하며 대응 체계를 설계하는 과정을 경험했다.
