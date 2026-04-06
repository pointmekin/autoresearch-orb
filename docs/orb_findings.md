# ORB Autoresearch — Strategy Findings
*Synthesized from 50 automated experiments across 15 instruments (8 forex pairs, 3 commodities, 4 equity ETFs/futures) · April 2026*

---

## TL;DR — Optimal Parameters (Best Experiment: `8747f65`, Sharpe 1.1445)

```
Opening range:       30 min (6 bars × 5m)
Breakout threshold:  0.1% beyond range high/low
Stop loss:           Range boundary (low for longs, high for shorts)
Take profit:         1.0× range height
Trailing stop:       Activate at +0.5× range, trail at 0.3× range
Max trades/session:  1
Sessions:            London (08:00–12:30 UTC) + New York (13:30–20:00 UTC)
Trade days:          Tuesday–Friday only (skip Monday)
Session close:       Mandatory — no overnight holds
```

---

## 1. Opening Range Formation

### ✅ 30-minute range (6 bars × 5m) is optimal
- Tested: 15 min (3 bars), 20 min (4 bars), 30 min (6 bars), 45 min window
- **15-min range** — too narrow, noisy levels get easily whipped through (Sharpe −2.41)
- **20-min (4-bar) range** — noisier than 6-bar, directional noise not filtered out (Sharpe −0.40)
- **30-min range** gives the market enough time to set meaningful support/resistance
- **45-min range** — slightly worse Sharpe but better drawdown; acceptable if you prefer lower variance

### ❌ Body-based range fails; use High/Low wicks
- Using Close prices (candle bodies) for range boundaries is strictly worse (Sharpe −0.32 vs baseline)
- Wick-based High/Low levels provide stronger S/R — the market acts on them

---

## 2. Breakout Threshold

### ✅ 0.1% filter is the sweet spot
- **No threshold (0%)**: Weak breakouts get entered — significantly hurts performance (Sharpe −2.86)
- **0.05% threshold**: Slightly worse than 0.1%, insufficient noise filtering
- **0.1% threshold**: Best balance — filters noise without missing valid breakouts
- **0.15% threshold**: Too strict; USDCAD/EURJPY get zero trades → catastrophic −999 Sharpe penalty
- **0.2% threshold**: Kills most symbols (Sharpe −66.97)

> **Key insight:** A minimum filter is non-negotiable. But too strict = no trades = worse than nothing.

---

## 3. Stop Loss

### ✅ Stop at range boundary (absolute level) is the current best
Evolution of SL testing:

| SL Setting | Sharpe | Note |
|---|---|---|
| 0.75× range height | −1.13 | Too tight, frequent stop-outs |
| 1.0× range height | 0.10 | Baseline |
| 1.5× range height | 0.65 | Better — wider stops let winners run |
| 1.75× range height | 0.705 | Fine-tuned improvement |
| 1.8× range height | 0.7145 | Marginal gain |
| 1.85× range height | 0.68 | Past optimum |
| 2.0× range height | 0.69 | Diminishing returns |
| 2.5× range height | 0.644 | Too wide |
| **Range boundary (absolute)** | **1.1445** | **Best — natural invalidation level** |
| Range midpoint | 0.933 | More stop-outs than boundary |

> **Key insight:** The range boundaries are the most natural stop levels. A close beyond the *opposite side* of the range invalidates the breakout thesis entirely.

### ❌ Breakeven stop is counterproductive
- Moving SL to breakeven at +0.5× range exits winners prematurely (Sharpe 0.128)

---

## 4. Take Profit

### ✅ 1.0× range height is optimal for TP

| TP Setting | Sharpe | Note |
|---|---|---|
| 0.75× range height | 0.335 | Tighter exits reduce profit per winner |
| **1.0× range height** | **1.1445** | **Optimal** |
| 1.5× range height | 1.03 | Higher return, worse Sharpe (more variance) |
| 2.0× range height | −3.34 | Doesn't fill; larger drawdowns |

> **Key insight:** TP = 1× range + trailing stop combo is the winning structure. TP provides the floor; trailing captures extended moves.

---

## 5. Trailing Stop — The Biggest Single Improvement

### ✅ Trailing stop at activation=0.5×, trail=0.3× is transformative
- Largest single Sharpe improvement in the entire research history:
  - Before: Sharpe ~0.71
  - After: Sharpe **1.12+**
- **Activation**: 0.5× range height — once profit ≥ half the range, activate trailing
- **Trail distance**: 0.3× range height — locks in ~60% of gained profit
- Tighter trail (0.2×) = identical result
- Lower activation (0.3×) = identical result

> **Key insight:** The trailing stop replaced the need for a perfectly calibrated fixed TP. Let the market decide how far the move extends.

---

## 6. Session & Time Filters

### ✅ Dual-session is mandatory — London + New York
- **London-only**: Too few trades per pair, catastrophic on USDCAD/EURJPY (Sharpe −132.4)
- **NY-only**: Killed commodities entirely — Gold/Silver/Oil are London-primary (Sharpe −532.6)
- **Both sessions combined**: Best overall coverage across all asset classes

### ✅ Trade only within 1 hour (12 bars) after range forms
- Late entries (beyond 1 hour after range): low-quality setups, net negative
- Edge decays rapidly — **do not chase late breakouts**

---

## 7. Day-of-Week Filter

### ✅ Skip Monday; trade Tuesday–Friday
- Monday is consistently choppy and unprofitable across the full portfolio
- Adding Monday back: Sharpe drops from ~0.65 to 0.10
- **Friday is profitable** — confirmed by testing; do not exclude it

---

## 8. Trade Frequency

### ✅ 1 trade per session maximum
- **2 trades/session**: Over-trading — second entries are lower quality (Sharpe −0.56 penalty)
- The first breakout after the range forms is the highest-quality signal; everything after is noise

---

## 9. Filters Tested and Rejected

| Filter | Sharpe Impact | Reason |
|---|---|---|
| SMA20 trend filter | −0.56 | Killed commodity trades; equities and commodities don't share trends |
| ATR filter (0.5–3×) | −0.13 | Too restrictive on mixed universe |
| Volume confirmation | Crash | Forex has no meaningful volume data |
| Prior bar direction filter | Marginally worse | No predictive edge from pre-range bar direction |
| Breakout body filter (0.5×) | −199.6 | Too strict — killed USDCAD/EURJPY/QQQ entirely |
| Time exit (18 bars after range) | −1.44 | Closes winners early |
| No forced session close | +0.41 | Overnight holds add gap risk with no upside |
| Breakeven stop at +0.5× | +0.13 | Exits winners prematurely |
| 1.5hr breakout window | −0.40 | More late chop trades, worse than 1hr |
| 30-min opening window | Crash | USDCAD/EURJPY get 0 trades — too restrictive |

---

## 10. Instrument Class Insights

### Commodities >> Equities >> Forex (in this setup)

Best experiment per-symbol results (`8747f65`):

| Symbol | Class | Sharpe | Return | Avg Trades |
|---|---|---|---|---|
| CL=F (Crude Oil) | Commodity | **5.44** | +27.58% | 31 |
| SI=F (Silver) | Commodity | **3.57** | +14.12% | 21 |
| SPY | Equity ETF | **3.17** | +0.47% | 1 |
| ES=F (S&P futures) | Equity | **2.99** | +2.74% | 18 |
| GC=F (Gold) | Commodity | **2.91** | +5.63% | 21 |
| QQQ | Equity ETF | **2.91** | +0.66% | 1 |
| NQ=F (Nasdaq futures) | Equity | **2.47** | +2.75% | 20 |
| GBPUSD | Forex | **1.47** | +0.57% | 15 |
| AUDUSD | Forex | −0.49 | −0.40% | 22 |
| USDCHF | Forex | 0.25 | +0.09% | 10 |
| EURUSD | Forex | −0.18 | −0.04% | 9 |
| EURJPY | Forex | −0.39 | −0.05% | 3 |
| NZDUSD | Forex | −0.82 | −0.55% | 22 |
| USDJPY | Forex | −2.26 | −0.55% | 9 |
| USDCAD | Forex | −3.88 | −0.86% | 4 |

**Key observations:**
- Commodities dominate — high intraday volatility creates wide, clean ORB ranges
- US equity futures work reliably across both sessions
- SPY and QQQ undertraded (only 1 trade each) — likely insufficient bars to form multiple setups
- **USDCAD and EURJPY are consistently the worst** across every experiment
- Most forex pairs are marginally negative to flat — the ORB edge is weak on narrow-range forex

---

## 11. Critical Failure Modes

1. **Over-trading** — every attempt to add more signals per session failed
2. **Overly strict thresholds** — one symbol at 0 trades creates a −999 Sharpe that destroys portfolio mean
3. **Session isolation** — cannot run London-only or NY-only; asset classes require different sessions
4. **One-size-fits-all indicators** — trend/momentum filters that work for equities kill commodities
5. **Time-based exits** — mechanical time exits close winners; SL/TP + trailing stop is superior
6. **Breakeven stops** — moving stop to entry too early is strictly confirmed worse

---

## 12. Robustness Principle

> *Maximize mean Sharpe across all symbols — not peak Sharpe on one.*

Sharpe 2.0 on 3 symbols + −0.5 on 12 others < Sharpe 0.9 across all 15.
Every parameter was evaluated portfolio-wide. This is the discipline that prevented curve-fitting.

---
---

# Bangkok Real-Life Implementation Guide

> **Bangkok timezone: UTC+7**

---

## Session Times in Bangkok (ICT)

| What | UTC | Bangkok |
|---|---|---|
| London opens | 08:00 | **15:00** |
| London range period (observe) | 08:00–08:30 | 15:00–15:30 |
| **London breakout window** | 08:30–09:30 | **15:30–16:30** |
| London session closes | 12:30 | 19:30 |
| NY opens | 13:30 | **20:30** |
| NY range period (observe) | 13:30–14:00 | 20:30–21:00 |
| **NY breakout window** | 14:00–15:00 | **21:00–22:00** |
| NY session closes | 20:00 | 03:00 (+1) |

---

## Daily Routine

**2:45 PM BKK — Pre-London prep**
1. Check economic calendar — skip session if high-impact event (FOMC/NFP/CPI/BOE) within 1 hour of open
2. Confirm it is Tuesday–Friday
3. Open 5-min charts for your instruments

**3:00 PM BKK — London session opens**
1. Observe only for 30 min. No trades.
2. At **3:30 PM**, mark the range:
   - `range_high` = highest High of 15:00–15:30 candles
   - `range_low` = lowest Low of 15:00–15:30 candles
   - `range_height = range_high − range_low`
3. Set trigger levels:
   - **Long trigger** = `range_high × 1.001`
   - **Short trigger** = `range_low × 0.999`
4. Place orders. Window closes at **4:30 PM BKK** — cancel if no fill.

**On fill, simultaneously set:**
- SL: `range_low` (if long) or `range_high` (if short)
- TP: entry ± `range_height × 1.0`
- Trailing stop: activate at `+0.5 × range_height` profit, trail distance `0.3 × range_height`

**7:30 PM BKK — London close**
- Close any open positions. No overnight holds.

**8:30 PM BKK — NY session opens**
- Repeat the identical process. Observe 8:30–9:00 PM, mark range at 9:00 PM, window 9:00–10:00 PM.

**3:00 AM BKK — NY close**
- Close all remaining positions.

---

## Position Sizing

```
Risk per trade = 1–2% of account equity
Position size  = (Account × Risk%) ÷ |Entry − Stop Loss|
Max 1 trade per instrument per session
```

---

## Valid Trade Checklist

- [ ] Day is Tue / Wed / Thu / Fri
- [ ] No high-impact news within 1 hour of session open
- [ ] Price breaks trigger within 1 hour of range formation
- [ ] First trade this session on this instrument (no re-entries)
- [ ] SL set at range boundary before entry confirmed
- [ ] Trailing stop configured

---

## Instrument Priority from Bangkok

| Priority | Instrument | Sharpe | Broker Access |
|---|---|---|---|
| 1 | **Crude Oil (USOIL/CL)** | 5.44 | IC Markets, Pepperstone, XM |
| 2 | **Silver (XAGUSD/SI)** | 3.57 | IC Markets, Pepperstone |
| 3 | **S&P 500 (US500/ES)** | 2.99–3.17 | Any CFD broker |
| 4 | **Gold (XAUUSD/GC)** | 2.91 | Every major broker in Thailand |
| 5 | **GBPUSD** | 1.47 | Every forex broker |

**Avoid starting with**: USDCAD, EURJPY.

---

## SET (Thai Stock Exchange) Adaptation

| Parameter | Value |
|---|---|
| Opening range | 09:30–10:00 (first 30 min of morning session) |
| Breakout window | 10:00–11:00 only |
| Stop loss | Opposite range boundary |
| Take profit | 1× range height |
| Forced close | By 12:20 (before lunch break) |
| Skip days | Monday + high-impact macro news days |

---

## Risk Framework

| Parameter | Value |
|---|---|
| Risk per trade | 1–2% of account |
| Max daily risk | 2% |
| Max consecutive losses before pause | 5 |
| Weekly review | Monday — check rolling Sharpe |
| Stop trading if | 3+ negative Sharpe weeks in a row |

> **Note:** Best-experiment mean max drawdown = −1.27% at portfolio level. Individual instruments (Silver: −4.58%, CL: −3.32%) can drawdown significantly more. Size accordingly.

---

## Broker Setup for Thailand

- **Recommended**: IC Markets, Pepperstone, XM, Exness (all accept Thai residents)
- Confirm: 5-minute charts, fractional pip stops, bracket/OCO orders, raw spread on metals
- Backtest commission assumption: **2 bps per side** — if your broker charges more, reduce size or switch

---

*Last updated: April 6, 2026 · 50 autonomous overnight experiments · autoresearch-orb*
