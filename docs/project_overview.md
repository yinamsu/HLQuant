# HLQuant Project Overview

HLQuant is an advanced quantitative trading system focused on delta-neutral funding rate arbitrage on the Hyperliquid exchange.

## System Architecture

The system follows a modular `Main - Indicator - Execution` structure:

1.  **HyperliquidAPI (`hyperliquid_api.py`)**: 
    - Handles asynchronous communication with Hyperliquid API.
    - Implements robust error handling and rate-limiting (Exponential Back-off).
    - Correctly maps Perp symbols to Spot assets using token metadata.
2.  **DeltaNeutralStrategy (`strategy.py`)**:
    - Calculates annualized funding rates (APY).
    - Filters assets based on APY thresholds and Basis (Premium) constraints.
    - Implements "Slippage Guard" (virtual price penalties) and "Minimum Hold Time" (8 hours) to ensure profitability after fees.
    - Manages paper trading state via `paper_balance.json`.
3.  **Main Loop (`main.py`)**:
    - Orchestrates the scanning process every 60 seconds.
    - Manages the lifecycle of the bot and logging.

## Core Strategy: Delta-Neutral Funding Arbitrage

- **Goal**: Capture funding rate payments by going long in the Spot market and short in the Perp market for the same asset.
- **Filtering Logic**:
    - Entry APY: > 3.0% (Test mode) / > 15.0% (Production)
    - Max Premium: < 0.1% (To minimize arbitrage loss on entry)
    - Rebalancing Gap: 10% (Test mode) / 20% (Production)
- **Safety Mechanisms**:
    - **Slippage Guard**: +0.05% price penalty on spot buy and -0.05% on perp sell during virtual entry.
    - **Minimum Hold Time**: 8 hours to prevent capital erosion from frequent rebalancing and fees.

## Current Status
- [x] Base infrastructure setup.
- [x] DNS resolution issue fixed using `ThreadedResolver`.
- [x] Spot-Perp mapping logic corrected.
- [x] Initial paper trading entries successfully verified (APT, AVAX, GMT).
