# Three-minute demo

1. **Problem:** Quiz scores tell teachers who got an answer wrong, but not what they misunderstood.
2. **Teacher dashboard:** Sign in as `teacher@demo.com`, show misconception hotspots and suggested interventions.
3. **Student journey (sandbox or simulator):** Run `POST /api/demo/reset` first. In the USSD simulator use phone `+256700000026`, press `1` for English or `2` then `1` for Luganda, choose a wrong answer and show the SMS status. Only call it delivered if you confirmed handset delivery; sandbox acceptance is not delivery proof.
4. **Act:** On Misconception insights, click *Send revision SMS* for the learners who still show the misconception.
5. **Recovery (live):** Dial again from the same phone. It now serves the follow-up. Answer correctly, then show the dashboard recovery number move and the airtime reward. Explain the denominator: only learners with a completed follow-up count.
6. **Evidence:** If you have run a real teacher or learner session, record factual feedback on *Pilot feedback*. Say explicitly that these notes are self-reported and unverified. Never present seeded data as pilot results.
7. **Close:** Mwalimu — Understand. Teach. Improve. It helps teachers understand learner thinking, provide personalised support and measure progress.

Clearly label preloaded analytics as illustrative demo data.
