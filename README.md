# HLQuant

HLQuant project for advanced trading and quantitative analysis.

## Setup
- Python 3.10+
- Git account: yinamsu

## Core Strategy: Delta-Neutral Arbitrage
HLQuant는 시장의 방향성 리스크를 제거하고 안정적인 수익을 추구합니다.
- **Delta-Neutral**: 현물 매수와 선물 매도 포지션을 1:1로 유지하여 코인 가격 변동에 따른 손익을 상쇄(0)합니다.
- **Profit Source**: 무위험 지표인 **펀딩비(Funding Fee)** 수취와 선물/현물의 **가격 차이(Basis)** 수렴 수익을 취합니다.
- **Risk Control**: 0.05% 슬리피지 가드, 최소 8시간 보유 원칙, APY 기반 동적 리밸런싱을 통해 자산을 보호합니다.
> 상세 내용은 [STRATEGY_WHITEPAPER.md](docs/STRATEGY_WHITEPAPER.md)에서 확인하실 수 있습니다.

## Features
- [x] Nitro Trading Engine Integration
- [x] Multi-exchange Support
- [x] Advanced Backtesting Lab
- [x] **Auto Deployment (GitHub Actions) Enabled**
