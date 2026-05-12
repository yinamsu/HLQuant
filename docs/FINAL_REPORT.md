# HLQuant Project Final Deployment Report

## 1. 프로젝트 개요
Hyperliquid 거래소의 델타 중립(Delta Neutral) 차익거래 전략을 자동화하고, 이를 클라우드 서버에서 24시간 안정적으로 구동하기 위한 인프라 구축 프로젝트입니다.

## 2. 시스템 아키텍처
- **언어**: Python 3.10+
- **핵심 모듈**:
  - `main.py`: 메인 루프 (시장 스캔 및 명령어 리스너 통합)
  - `hyperliquid_api.py`: 거래소 통신 및 데이터 전처리
  - `strategy.py`: 델타 중립 진입/청산/리밸런싱 로직
  - `notifier.py`: 텔레그램 알림 및 시스템 모니터링 (`psutil` 연동)
- **배포**: GitHub Actions (CI/CD) -> GCP VM Instance

## 3. 인프라 구성 내역
- **서버 호스트**: GCP (IP: 34.136.45.224)
- **운영 환경**: Ubuntu Linux (Managed via systemd)
- **보안 설정**:
  - `.env` 파일을 통한 환경 변수 격리 (API Key, SSH Key, Bot Token)
  - 전용 SSH Deploy Key를 이용한 자동화된 코드 접근 권한 부여
- **서비스 자동화**: `hlquant.service` 등록으로 부팅 시 자동 시작 및 크래시 발생 시 자동 재시작.

## 4. 텔레그램 봇 시스템 (HLQuantBot)
- **알림 기능**:
    - 가상 진입/청산 시 실시간 알림 전송 (APY, 가격 정보 포함)
    - 봇 시작/종료 시 가동 상태 보고
- **인터랙티브 명령어**:
    - `/server`: 서버 리소스(CPU, RAM, SWAP, DISK) 상태 보고 (Alpha Dashboard 디자인)
    - `/help`: 명령어 도움말 제공
- **지능형 기능**:
    - **중복 답변 방지**: `last_update_id` 추적을 통해 동일 명령어에 한 번만 응답.
    - **시작 시 큐 클리어**: 가동 직전의 과거 메시지들을 무시하여 도배 방지.

## 5. CI/CD 배포 파이프라인
1. **Push**: 로컬에서 `main` 브랜치로 코드 푸시.
2. **Action**: GitHub Actions가 트리거되어 서버에 SSH 접속.
3. **Deploy**: `deploy.sh` 실행 (최신 코드 Pull -> 의존성 설치 -> 서비스 재시작).
4. **Notify**: 봇이 재시작되며 텔레그램으로 가동 시작 알림 전송.

## 6. 유지보수 가이드
- **서비스 상태 확인**: `sudo systemctl status hlquant.service`
- **실시간 로그 모니터링**: `journalctl -u hlquant.service -f`
- **수동 재시작**: `sudo systemctl restart hlquant.service`
- **설정 변경**: 서버의 `~/HLQuant/.env` 파일 수정 후 서비스 재시작.

---
**작성일**: 2026-05-12
**상태**: 운영(Production) Ready - 가상 매매 모드 가동 중
