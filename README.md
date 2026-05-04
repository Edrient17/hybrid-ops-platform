# Hybrid Ops Platform

온프레미스 Kubernetes와 AWS ECS를 연계한 하이브리드 웹서비스 운영 및 장애 대응 자동화 플랫폼이다.

## 1. 프로젝트 개요

이 프로젝트는 로컬 가상화 환경 기반의 온프레미스 Kubernetes 클러스터와 AWS ECS 환경을 연계하여 웹 서비스를 운영하고, 모니터링, 로그 수집, 자동 배포, 장애 알림, 장애 로그 요약 기능까지 포함한 하이브리드 운영 플랫폼을 구축하는 것을 목표로 한다.

## 2. 전체 구성

```text
Local On-Premise
├── VMware
│   ├── k3s-control-01
│   ├── k3s-worker-01
│   └── k3s-worker-02
│
├── k3s Cluster
│   ├── Internal Ops API
│   ├── Prometheus
│   ├── Grafana
│   ├── Loki
│   └── Promtail
│
AWS
├── ECR
├── ECS Fargate
├── ALB
├── CloudWatch
├── EventBridge
├── Lambda
└── S3