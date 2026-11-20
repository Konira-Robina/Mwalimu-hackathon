# API contract

Teacher endpoints require the short-lived bearer token returned by `POST /api/auth/login`. `POST /api/auth/logout` revokes the current token. Set `SESSION_TTL_HOURS` to adjust expiry.

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/dashboard/overview`
- `GET|POST /api/classes`
- `GET|POST /api/students`
- `GET|POST /api/questions`
- `GET /api/assessments`
- `GET /api/analytics/misconceptions`
- `GET /api/analytics/recovery`
- `POST /api/ussd/callback` (form-urlencoded Africa's Talking callback)
- `GET /api/ussd/status`
- `POST /api/at/sms/delivery-report` (Africa's Talking asynchronous SMS delivery report)
- `POST /api/at/airtime/delivery-report` (Africa's Talking asynchronous airtime status)
- `POST /api/at/ussd/event` (USSD session duration, cost, and status event)
- `GET /api/analytics/ussd-sessions` (authenticated USSD session summary)
- `POST /api/misconceptions/{id}/notify` (SMS revision tip to learners still showing it; optional body `{"message": "..."}`)
- `GET /api/rewards` (airtime rewards)
- `GET|POST /api/pilot/observations` (self-reported educator/learner feedback; do not include personal identifiers)
- `POST /api/demo/reset` (clears live demo attempts, learners 026–030, and the SMS log)
- `GET /api/ussd/messages` (authenticated SMS log; optional `phoneNumber` filter)

The USSD callback replies `text/plain` starting with `CON` or `END`. Optional `?key=` is checked when `USSD_CALLBACK_SECRET` is set.

USSD callback fields: `sessionId`, `serviceCode`, `phoneNumber`, `text`.
The web simulator sends `X-Mwalimu-Simulator: true` and requires a teacher session. Simulator SMS stays local unless the configured provider is the Africa's Talking Sandbox. The first USSD menu offers English (`1`) or Luganda (`2`), then `1` starts the quiz. Enter `0` at any point to end a simulator session. Add teacher-reviewed Luganda question, answer, and feedback text to the question bank; untranslated question text falls back to English.

Callback payloads accept form-urlencoded or JSON. SMS uses `messageId` (or `id`) and `status`; airtime uses `requestId` and `status`; USSD events use `sessionId`, `duration`, `cost`, `currencyCode`, and `status`. Add `?key=...` to callback URLs when the corresponding `AT_*_CALLBACK_SECRET` is configured. Configure the SMS and airtime delivery-report callbacks and the separate USSD event URL in the Africa's Talking dashboard. Callback events arriving before their API response are buffered and reconciled by provider ID.
