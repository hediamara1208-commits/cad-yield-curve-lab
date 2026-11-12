# Learning Notes

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

### Questions to review

1. Why can't DF(3) be computed before DF(2)?
2. If bond C's price drops (A and B unchanged), what happens to DF(3) and z(3)?
3. Why does a rising zero curve imply forwards above the zero curve?
