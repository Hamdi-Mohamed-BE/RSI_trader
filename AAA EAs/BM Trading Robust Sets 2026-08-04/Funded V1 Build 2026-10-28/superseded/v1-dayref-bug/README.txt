v1 package superseded 2026-10-28: the day reference recorded at the first tick was not moved by same-day withdrawals, so a payout
looked like a daily loss (false close-all + false firm-breach latch). Found by the harness (withdrawal step). v2 stores the balance-operation
total with the reference and moves it by later withdrawals / deposits. Kept as evidence, not for use.
