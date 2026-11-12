# Learning Notes

## English → French glossary

| English | Français |
|---|---|
| Discount factor | Facteur d'actualisation |
| Discounting / present value | Actualisation / valeur actuelle |
| Bond | Obligation |
| Face value / par / principal | Valeur nominale / nominal / pair |
| Coupon | Coupon |
| Maturity | Échéance |
| Yield curve | Courbe de rendement (usage canadien) / courbe des taux (usage français) |
| Zero-coupon rate / spot rate | Taux zéro-coupon / taux au comptant |
| Forward rate | Taux à terme |
| Yield to maturity | Rendement à l'échéance |
| Fixed income | Titres à revenu fixe |
| Basis point (bp) | Point de base (pb) |
| Accrued interest | Intérêts courus |
| Clean / dirty price | Prix sans / avec intérêts courus |
| Bootstrapping | Bootstrap (terme gardé en anglais) |

## Session 1 (2026-11-12): bootstrapping foundations

### Key concepts

- **A bond is a list of future cash flows.** 3-year, 3.5% annual coupon, face 100 → 3.5 / 3.5 / 103.5.
- **Discount factor DF(t)**: today's value of 1 $ received at time t. 0 < DF ≤ 1 when rates are positive.
- **Pricing equation**: `P = Σ CF(t) · DF(t)`.
- **Zero rate** (annual compounding): `DF(T) = 1/(1+z)^T`, i.e. `z(T) = DF(T)^(-1/T) - 1`. Just a different way to express DF.
- **Forward rate**: `f(T1,T2) = [DF(T1)/DF(T2)]^(1/(T2-T1)) - 1`. The rate implied today for borrowing between T1 and T2.

### Why bootstrapping is sequential

A bond maturing at T has only one cash flow at a date with an unknown DF: the last one. All earlier DFs come from shorter bonds. One equation, one unknown:

`DF(T) = [P - 100·c·Σ_{t<T} DF(t)] / [100·(1+c)]`

### Worked example (synthetic data)

| Step | Equation | Result |
|---|---|---|
| A (1y, 0%) | 97.0874 = 100·DF(1) | DF(1)=0.970874, z=3.00% |
| B (2y, 3%) | 99.6241 = 3·0.970874 + 103·DF(2) | DF(2)=0.938946, z=3.20% |
| C (3y, 3.5%) | 100.3065 = 3.5·(0.970874+0.938946) + 103.5·DF(3) | DF(3)=0.904562, z=3.40% |

Forward f(1,2) = 0.970874/0.938946 − 1 = 3.40%. It is above both zero rates (3.00% and 3.20%) because the zero rate is an average of forwards: when the zero curve rises, the forward curve lies above it.

### Yield to maturity vs zero rate (mistake corrected)

- **My answer:** with a flat curve at 3.40%, bond C's yield would be *below* z(3).
- **Correction:** with a flat curve every cash flow is discounted at 3.40%, so the YTM is exactly 3.40% = z(3). The yield differs from z(T) only when the curve is not flat.
- **Rising curve (our reference):** YTM(C) ≈ 3.39% < z(3) = 3.40%. The coupons at t=1 and t=2 are discounted at lower rates (3.00%, 3.20%), and the YTM is a cash-flow-weighted average of the zero rates, dominated by the final flow (103.5).
- Rising curve → coupon bond YTM < z(T). Falling curve → YTM > z(T). Flat curve → equal. A higher coupon puts more weight on early flows, so it widens the gap.

### Price vs face value (mistake corrected)

- **My confusion:** I thought the buyer pays 100 today, and that longer bonds cost more.
- **Correction:** the **price** is what I pay today. The **face value** (100) is what I receive at maturity. For a zero-coupon bond: price = 100 × DF(T) < 100.
- Example: 100 received in 5 years costs 83.59 today, because 83.59 × 1.0365^5 = 100. The difference (16.41) is my pay for lending the money for 5 years.
- The later the money arrives, the less it is worth today. Longer zero-coupon bond → lower price. In our dataset, prices rise with maturity only because the coupons were chosen to rise too.

### Rates up → discount factors down → prices down

- Taux d'actualisation (z) ≠ facteur d'actualisation (DF). When z goes up, DF goes down.
- Example: z(4) from 3.55% to 3.80% (+25 bp) → DF(4) from 0.8698 to 0.8614.
- Intuition: DF is the amount to invest today to get 1 $ later. A higher bank rate means less money is needed today, so a promise of 1 $ later is worth less.
- 1 basis point = 0.01% = 0.0001. Always say "points de base", never just "points".

### Forward rates (taux à terme)

- f(2,3) = rate fixed **today** for a loan that starts in year 2 and ends in year 3.
- **Zero rate = average of forwards.** z(3) ≈ (3.00 + 3.40 + 3.80) / 3 = 3.40%. Like a grade average: to make it rise, the new grade must be above the average. Rising curve → forwards above zero rates; flat → equal; inverted → below.
- **Replication with zero-coupon bonds** (single payment, no coupons). Today: borrow 90.46 for 2 years (repay 90.46/DF(2) = 96.34 in year 2) and invest it in a 3-year zero-coupon paying 100. Net today: 0. Year 2: pay 96.34. Year 3: receive 100. Rate locked today: 100/96.34 − 1 = 3.80% = f(2,3).
- **No arbitrage:** this construction earns nothing for free. That is what forces the forward to be 3.80%.
- **A forward rate is not a prediction** of the future rate. It is the rate that can be locked today. Investors often demand a term premium, so forwards tend to sit a bit above expectations.

### Arbitrage, speculation, hedging

| Strategy | Risk | Gain |
|---|---|---|
| Arbitrage (market quotes a forward ≠ implied rate) | none | small, rare, closed in seconds |
| Speculation (bet that the future rate ≠ forward) | yes | depends on my forecast |
| Hedging (lock a rate to remove uncertainty) | reduced | not the goal |

- "Fair price" means **nobody can win for sure in advance**, not that nobody wins. Like a fair coin toss.
- A forward contract is a **zero-sum game**: the lender's gain is the borrower's loss.

### Which side to take (mistake corrected)

- **My mistake:** I said "if rates will rise, be the lender".
- **Correction:** lock today the rate that becomes attractive tomorrow.
  - Rates will **rise** → borrowing becomes expensive → lock a **borrowing** rate now.
  - Rates will **fall** → lending pays less → lock a **lending** rate now.
- Consistency check: lending = owning a bond, and bond prices rise when rates fall.

### Who sets forward rates (mistake corrected)

- **My confusion:** contracts registered with the central bank, which sets forward rates.
- **Correction:** forward rates come from **market prices** (bond prices, via our formula). The **Bank of Canada** (Banque du Canada, the central bank) sets only the overnight **policy rate** (taux directeur); it strongly drives short rates. The **Banque Nationale du Canada** is a commercial bank, not the central bank.
- Forward rates change every day; contracts are revalued daily (**mark-to-market**).

### Forwards vs futures

| | Forward (de gré à gré, OTC) | Future (standardised, exchange) |
|---|---|---|
| Where | negotiated between two parties | on an exchange (e.g. Bourse de Montréal, CORRA futures) |
| Terms | custom | standardised |
| Settlement | usually at maturity | **daily** (margin calls) |
| Counterparty risk | yes | almost none (clearing house) |

- OTC derivatives must be reported to regulators since 2008 (in Quebec: the AMF).
- Further reading: Hull, *Options, Futures, and Other Derivatives*, first chapters (futures and forward markets).

### Questions to review

1. Why can't DF(3) be computed before DF(2)?
2. If bond C's price drops (A and B unchanged), what happens to DF(3) and z(3)?
3. Why does a rising zero curve imply forwards above the zero curve?
4. Show with zero-coupon bonds how to lock f(2,3) today with no money out.
5. You expect rates to fall: lender or borrower in a forward? Why?
6. Name two differences between a forward and a future.
