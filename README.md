# HLQuant: Hyperliquid Delta-Neutral Bot

![Hyperliquid](https://img.shields.io/badge/Exchange-Hyperliquid-6347FF?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Live_Trading-green?style=for-the-badge)
![Strategy](https://img.shields.io/badge/Strategy-Delta_Neutral-blue?style=for-the-badge)

하이퍼리퀴드(Hyperliquid) 거래소 전용 델타 중립(Delta-Neutral) 자산 운용 봇입니다. 현물 매수와 선물 매도를 동시에 실행하여 방향성 리스크를 제거하고, 펀딩비 수익을 안정적으로 수확합니다.

## 🚀 최근 주요 업데이트 및 연구 결과

### 1. 현물-선물 매핑 정밀 연구 완료 (2026-05-15)
*   **연구 결론**: 하이퍼리퀴드 현물 시장의 특수성으로 인해 **현재 실질적인 델타 중립 거래가 가능한 종목은 `PURR` 단 1종목**입니다.
*   **주의 사항**: `BTC`, `ETH`, `HYPE` 등은 현물 이름과 선물 심볼이 같더라도 실제로는 가격이 전혀 다른 별개 자산(Wrapped Token 또는 동명이인 토큰)인 경우가 많습니다.
*   **안전 조치**: `spot_mapping.json`은 오직 100% 검증된 `PURR` 전용 매핑(`PURR/USDC`)으로 유지됩니다.

### 2. 실행 안정성 강화
*   **Spot-First 주문 체결**: 네이키드 포지션(Naked Position) 방지를 위해 반드시 현물 체결 성공 후 선물을 주문합니다.
*   **안전 재시작 로직**: 배포 시 중복 프로세스 충돌 및 알림 중복을 방지하기 위해 `Stop -> Sleep -> Start` 시퀀스가 적용된 `deploy.sh`를 사용합니다.
*   **프리미엄 가드 강화**: 베이시스 리스크를 원천 차단하기 위해 프리미엄 가드 임계치를 **-0.05%**로 상향 조정했습니다.

## 🛠️ 운영 가이드

### 텔레그램 명령어
*   `/status`: 현재 봇의 가동 상태 및 최신 스캔 데이터 확인
*   `/balance`: 포트폴리오 요약 (현물 잔고 + 선물 증거금)
*   `/positions`: 현재 열려 있는 델타 중립 포지션 상세 내역
*   `/logs`: 서버의 최신 실행 로그 10줄 확인

### 배포 및 재시작
```bash
# 코드 수정 후 푸시 시 GitHub Action에 의해 자동 배포됩니다.
git push origin main
```

## 📊 기대 수익 및 리스크 관리
*   **기대 수익**: 실시간 펀딩비 기준 월 약 1.5% ~ 2.5% (연 복리 20%~30% 수준)
*   **위험 관리**:
    *   **Basis Risk**: 진입 시 선물-현물 괴리(Premium)가 -0.05% 이하일 경우 진입 금지.
    *   **Negative APY**: 펀딩비가 음수로 전환되어 손실 발생 시 즉시 비상 탈출 실행.

---
**주의**: 본 봇은 실거래용이며, 하이퍼리퀴드 현물 시장의 유동성 및 매핑 구조를 완벽히 이해한 후 사용해야 합니다.
