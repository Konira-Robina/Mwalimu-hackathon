# API contract

Teacher endpoints require `Authorization: Bearer radar-demo-token`.

- `POST /api/auth/login`
- `GET /api/dashboard/overview`
- `GET|POST /api/classes`
- `GET|POST /api/students`
- `GET|POST /api/questions`
- `GET /api/assessments`
- `GET /api/analytics/misconceptions`
- `GET /api/analytics/recovery`
- `POST /api/ussd/callback` (form-urlencoded Africa's Talking callback)
- `GET /api/ussd/status`
- `GET /api/ussd/messages` (authenticated SMS log; optional `phoneNumber` filter)

USSD callback fields: `sessionId`, `serviceCode`, `phoneNumber`, `text`.
The web simulator sends `X-Mwalimu-Simulator: true`; simulator SMS stays local unless the configured provider is the Africa's Talking Sandbox. Enter `0` at any point to end a simulator session.
