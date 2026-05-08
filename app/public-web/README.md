# Public Web App

AWS ECS Fargate에 배포할 외부 공개용 Flask 웹 애플리케이션

## Endpoint

| Endpoint | Description |
|---|---|
| `/` | 서비스 기본 정보 |
| `/health` | 헬스체크 |
| `/version` | 버전 정보 |
| `/status/internal` | Internal Ops API 연계 상태 |
| `/error` | 500 에러 장애 테스트 |
| `/slow` | 지연 응답 테스트 |
| `/stress` | CPU 부하 테스트 |

## Local Run

```bash
pip install -r requirements.txt
python app.py
```

## Docker Run
```
docker build -t public-web-app:v0.1.0 .
docker run -p 5000:5000 public-web-app:v0.1.0
```

## Test
```
curl http://localhost:5000/health
curl http://localhost:5000/version
curl http://localhost:5000/error
curl "http://localhost:5000/slow?delay=3"
curl http://localhost:5000/stress
```
