import json
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "sample_incident.json"
OUTPUT_DIR = BASE_DIR / "output"


def load_incident(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_metric_name(event: dict) -> str:
    raw_event = event.get("raw_event", {})
    detail = raw_event.get("detail", {})
    configuration = detail.get("configuration", {})
    metrics = configuration.get("metrics", [])

    try:
        return metrics[0]["metricStat"]["metric"]["name"]
    except (IndexError, KeyError, TypeError):
        return "unknown"


def extract_reason(event: dict) -> str:
    raw_event = event.get("raw_event", {})
    detail = raw_event.get("detail", {})
    state = detail.get("state", {})
    return state.get("reason", "No reason provided")


def build_summary(event: dict) -> str:
    project = event.get("project", "unknown")
    environment = event.get("environment", "unknown")
    received_at = event.get("received_at", "unknown")
    alarm_name = event.get("alarm_name", "unknown")
    new_state = event.get("new_state", "unknown")
    source = event.get("source", "unknown")
    region = event.get("region", "unknown")
    metric_name = extract_metric_name(event)
    reason = extract_reason(event)

    generated_at = datetime.utcnow().isoformat() + "Z"

    return f"""# Incident Summary

## 1. 기본 정보

- 프로젝트: {project}
- 환경: {environment}
- 리전: {region}
- 이벤트 수신 시각: {received_at}
- 요약 생성 시각: {generated_at}
- 이벤트 소스: {source}

## 2. 감지 정보

- Alarm 이름: {alarm_name}
- Alarm 상태: {new_state}
- 감지 Metric: {metric_name}
- 상태 변경 사유:
  - {reason}

## 3. 장애 요약

Public Web App에서 5XX 응답이 발생했고, ALB Target 5XX 지표가 임계치를 초과하여 CloudWatch Alarm이 ALARM 상태로 전환되었습니다.

이 이벤트는 EventBridge Rule을 통해 Lambda로 전달되었고, Lambda가 장애 이벤트 원문을 S3에 JSON 형식으로 저장했습니다.

## 4. 원인 후보

- `/error` endpoint 호출로 인한 의도적 500 에러 발생
- 애플리케이션 내부 예외 또는 비정상 응답
- ECS Task 내부 애플리케이션 오류
- 배포 버전 또는 환경변수 설정 문제
- 외부 의존 서비스 호출 실패 가능성

## 5. 1차 점검 항목

1. ALB Target Group의 Healthy Host 상태를 확인한다.
2. CloudWatch Logs에서 Public Web App 로그를 확인한다.
3. `/error` 호출 시점의 애플리케이션 로그를 확인한다.
4. ECS Service 이벤트에서 Task 재시작 또는 배포 실패 여부를 확인한다.
5. 최근 배포된 이미지 태그와 Task Definition revision을 확인한다.
6. 장애가 의도된 테스트인지 실제 서비스 오류인지 구분한다.

## 6. 대응 절차 초안

1. CloudWatch Alarm 발생 시각을 기준으로 관련 로그를 조회한다.
2. `/error` endpoint 호출에 의한 테스트 장애라면 정상 테스트로 기록한다.
3. 실제 장애라면 ECS Task 로그와 ALB Target 상태를 확인한다.
4. 애플리케이션 오류가 확인되면 직전 배포 버전으로 롤백하거나 수정 이미지를 배포한다.
5. 장애 원인, 영향 범위, 조치 내용을 장애 보고서에 기록한다.

## 7. 장애 보고서 초안

- 장애명: Public Web App 5XX 응답 증가
- 발생 시각: {received_at}
- 감지 방식: CloudWatch Alarm `{alarm_name}`
- 영향 범위: ALB를 통해 Public Web App에 접근한 요청 중 일부가 500 응답을 수신
- 원인 후보: 애플리케이션 오류 또는 의도적 장애 테스트 endpoint 호출
- 조치 내용: CloudWatch Logs, ECS Service 이벤트, ALB Target 상태 확인 필요
- 후속 조치: 장애 재현 여부 확인 및 필요 시 애플리케이션 수정/재배포
"""


def main() -> None:
    incident = load_incident(INPUT_FILE)
    summary = build_summary(incident)

    OUTPUT_DIR.mkdir(exist_ok=True)

    output_file = OUTPUT_DIR / "incident_summary.txt"
    with output_file.open("w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Incident summary created: {output_file}")


if __name__ == "__main__":
    main()