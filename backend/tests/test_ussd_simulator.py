import tempfile
import hashlib
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app import main

AUTH = {"Authorization": "Bearer radar-test-session"}
PHONE_1 = "+256700000001"
PHONE_2 = "+256700000002"


def seed_test_data(db):
    teacher = main.Teacher(name="Test teacher", email="teacher@test.local", password_hash="test")
    db.add(teacher)
    db.flush()
    classroom = main.SchoolClass(teacher_id=teacher.id, name="Test class", subject="Science")
    db.add(classroom)
    db.flush()
    db.add_all([
        main.Student(class_id=classroom.id, student_code="001", name="Learner one", phone_number=PHONE_1),
        main.Student(class_id=classroom.id, student_code="002", name="Learner two", phone_number=PHONE_2),
    ])
    misconception = main.Misconception(
        name="Test misconception", description="Test description", topic="Test topic", intervention="Test intervention"
    )
    db.add(misconception)
    db.flush()

    questions = [
        main.Question(class_id=classroom.id, text="Question one?", topic="One"),
        main.Question(class_id=classroom.id, text="Question two?", topic="Two"),
        main.Question(class_id=classroom.id, text="Question three?", topic="Three"),
    ]
    db.add_all(questions)
    db.flush()
    # Q1 and Q3: A is wrong (mapped to the misconception), B is correct. Q2: A is correct.
    for index, question in enumerate(questions):
        wrong_misconception = misconception.id if index in (0, 2) else None
        db.add_all([
            main.Option(question_id=question.id, label="A", text="Wrong answer",
                        is_correct=index == 1, misconception_id=wrong_misconception,
                        feedback="Tip: think again about this idea." if index != 1 else ""),
            main.Option(question_id=question.id, label="B", text="Correct answer", is_correct=index != 1),
        ])
    for title, kind in (("Test baseline", "baseline"), ("Test follow-up", "followup")):
        assessment = main.Assessment(class_id=classroom.id, title=title, kind=kind)
        db.add(assessment)
        db.flush()
        for position, question in enumerate(questions):
            db.add(main.AssessmentQuestion(assessment_id=assessment.id, question_id=question.id, position=position))
    db.commit()


def seed_test_app(db):
    seed_test_data(db)
    teacher = db.query(main.Teacher).one()
    db.add(main.TeacherSession(
        token_hash=hashlib.sha256(b"radar-test-session").hexdigest(),
        teacher_id=teacher.id,
        expires_at=int(time.time()) + 3600,
    ))
    db.commit()


@pytest.fixture
def isolated_database(monkeypatch):
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        engine = create_engine(
            f"sqlite:///{(Path(directory) / 'ussd-test.db').as_posix()}",
            connect_args={"check_same_thread": False},
        )
        main.Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        monkeypatch.setattr(main, "SessionLocal", TestSession)
        monkeypatch.setattr(main.settings, "at_enabled", False)
        monkeypatch.setattr(main.settings, "openrouter_api_key", "")
        monkeypatch.setattr(main.settings, "ussd_callback_secret", "")
        # Seed isolated data and a test-only bearer session at application startup.
        monkeypatch.setattr(main, "seed", seed_test_app)
        yield TestSession
        engine.dispose()


def dial(client, session_id, phone, text, simulator=True, params=None):
    headers = {"X-Mwalimu-Simulator": "true", "Authorization": "Bearer radar-test-session"} if simulator else {}
    return client.post(
        "/api/ussd/callback",
        data={"sessionId": session_id, "serviceCode": "*123#", "phoneNumber": phone, "text": text},
        headers=headers,
        params=params,
    )


def test_registered_phone_quiz_returns_plain_text_with_real_newlines(isolated_database):
    TestSession = isolated_database
    with TestClient(main.app) as client:
        sid = "s-one"
        welcome = dial(client, sid, PHONE_1, "")
        # Africa's Talking needs a plain-text body starting with CON/END (not a JSON string).
        assert welcome.headers["content-type"].startswith("text/plain")
        assert welcome.text.startswith("CON Welcome to Mwalimu\n")
        assert "\\n" not in welcome.text
        # Registered phone: no learner-ID step.
        assert dial(client, sid, PHONE_1, "1").text.startswith("CON Q1:")
        assert dial(client, sid, PHONE_1, "1*9").text.startswith("CON Invalid selection")
        assert dial(client, sid, PHONE_1, "1*9*1").text.startswith("CON Q2:")
        assert dial(client, sid, PHONE_1, "1*9*1*1").text.startswith("CON Q3:")
        assert dial(client, sid, PHONE_1, "1*9*1*1*1").text.startswith("END Quiz complete! Score: 1/3")

        messages = client.get("/api/ussd/messages", params={"phoneNumber": PHONE_1}, headers=AUTH).json()
        assert len(messages) == 2
        assert all(m["recipient"] == PHONE_1 and m["delivery_status"] == "demo" for m in messages)
        assert all(m["message"].startswith("MWALIMU\n") and "\\n" not in m["message"] for m in messages)

        with TestSession() as db:
            attempt = db.query(main.Attempt).one()
            assert attempt.completed and attempt.score == 1 and attempt.total == 3
            assert db.query(main.Response).filter_by(attempt_id=attempt.id).count() == 3


def test_unregistered_phone_falls_back_to_learner_id_and_sms_goes_to_dialler(isolated_database):
    stranger = "+256711111111"
    with TestClient(main.app) as client:
        sid = "s-stranger"
        assert dial(client, sid, stranger, "1").text.startswith("CON Enter your learner ID")
        assert dial(client, sid, stranger, "1*999").text.startswith("END Learner ID not found")
        sid = "s-stranger-2"
        assert dial(client, sid, stranger, "1*001").text.startswith("CON Q1:")
        assert dial(client, sid, stranger, "1*001*1").text.startswith("CON Q2:")
        assert dial(client, sid, stranger, "1*001*1*1").text.startswith("CON Q3:")
        assert dial(client, sid, stranger, "1*001*1*1*1").text.startswith("END Quiz complete")
        # Feedback goes to the handset that dialled, never to the typed-in learner's number.
        recipients = {m["recipient"] for m in client.get("/api/ussd/messages", headers=AUTH).json()}
        assert recipients == {stranger}


def run_quiz(client, sid, phone, answers):
    text = ""
    last = ""
    for answer in [None] + answers:
        text = "1" if answer is None else f"{text}*{answer}"
        last = dial(client, sid, phone, text).text
    return last


def test_followup_flow_recovery_and_airtime(isolated_database):
    TestSession = isolated_database
    with TestClient(main.app) as client:
        # Learner 1: wrong on Q1/Q3 at baseline, then fully correct in the follow-up -> recovered.
        assert run_quiz(client, "a1", PHONE_1, [1, 1, 1]).startswith("END Quiz complete! Score: 1/3")
        # Baseline alone must NOT count as recovery (no matched follow-up yet).
        overview = client.get("/api/dashboard/overview", headers=AUTH).json()
        assert overview["recovery_eligible"] == 0 and overview["recovery_rate"] == 0

        assert run_quiz(client, "a2", PHONE_1, [2, 1, 2]).startswith("END Quiz complete! Score: 3/3")
        # Third dial: both quizzes done.
        assert dial(client, "a3", PHONE_1, "1").text.startswith("END You have completed all")

        # Learner 2: repeats the misconception at follow-up -> not recovered, no reward.
        run_quiz(client, "b1", PHONE_2, [1, 1, 1])
        run_quiz(client, "b2", PHONE_2, [1, 1, 1])

        overview = client.get("/api/dashboard/overview", headers=AUTH).json()
        assert overview["recovery_eligible"] == 2
        assert overview["recovery_recovered"] == 1
        assert overview["recovery_rate"] == 50.0
        per = client.get("/api/analytics/recovery", headers=AUTH).json()["items"][0]
        assert (per["eligible"], per["recovered"]) == (2, 1)

        rewards = client.get("/api/rewards", headers=AUTH).json()
        assert len(rewards) == 1 and rewards[0]["phone"] == PHONE_1 and rewards[0]["status"] == "demo"
        texts = [m["message"] for m in client.get("/api/ussd/messages", headers=AUTH).json()]
        assert any("Airtime reward" in t for t in texts)


def test_no_airtime_for_typed_in_learner_id(isolated_database):
    stranger = "+256722222222"
    with TestClient(main.app) as client:
        run_quiz(client, "c1", PHONE_1, [1, 1, 1])  # baseline for learner 001 from their own phone
        text = ""
        for step in ["1", "001", 2, 1, 2]:  # follow-up for 001 from someone else's phone
            text = str(step) if not text else f"{text}*{step}"
            out = dial(client, "c2", stranger, text).text
        assert out.startswith("END Quiz complete! Score: 3/3")
        assert client.get("/api/rewards", headers=AUTH).json() == []


def test_notify_targets_only_learners_still_affected(isolated_database):
    with TestClient(main.app) as client:
        run_quiz(client, "n1", PHONE_1, [1, 1, 1])
        run_quiz(client, "n2", PHONE_2, [1, 1, 1])
        client.post("/api/demo/reset", headers=AUTH)  # clears the SMS log produced by the quizzes
        run_quiz(client, "n3", PHONE_1, [2, 1, 2])  # learner 1 recovers in follow-up

        mc = client.get("/api/analytics/misconceptions", headers=AUTH).json()[0]
        assert mc["currently_affected"] == 1  # learner 2 only; learner 1 recovered
        res = client.post(f"/api/misconceptions/{mc['id']}/notify", headers=AUTH, json={})
        assert res.status_code == 200
        sent = client.get("/api/ussd/messages", headers=AUTH).json()
        recipients = {m["recipient"] for m in sent if "Revision tip" in m["message"]}
        # Learner 1 has recovered; only learner 2 still shows the misconception.
        assert recipients == {PHONE_2}
        assert res.json()["queued"] == 1
        assert any("Tip: think again" in m["message"] for m in sent)
        assert client.post("/api/misconceptions/nope/notify", headers=AUTH).status_code == 404


def test_callback_secret_is_enforced_for_non_simulator_requests(isolated_database, monkeypatch):
    monkeypatch.setattr(main.settings, "ussd_callback_secret", "s3cret")
    with TestClient(main.app) as client:
        assert dial(client, "k1", PHONE_1, "", simulator=False).status_code == 403
        ok = dial(client, "k2", PHONE_1, "", simulator=False, params={"key": "s3cret"})
        assert ok.status_code == 200 and ok.text.startswith("CON Welcome")


class FakeSMS:
    """Mirrors the real SDK signature: SMS.send(message, recipients, sender_id=None, ...)."""
    def __init__(self, status_code="101"):
        self.status_code, self.calls = status_code, []

    def send(self, message, recipients, sender_id=None, enqueue=False, callback=None):
        self.calls.append({"message": message, "recipients": recipients, "sender_id": sender_id})
        return {"SMSMessageData": {"Recipients": [{"number": recipients[0], "statusCode": self.status_code}]}}


@pytest.mark.parametrize("code,expected", [("101", "accepted"), ("403", "failed")])
def test_sms_send_uses_sender_id_and_checks_gateway_status(monkeypatch, code, expected):
    import africastalking
    fake = FakeSMS(code)
    monkeypatch.setattr(africastalking, "initialize", lambda *a, **k: None)
    monkeypatch.setattr(africastalking, "SMS", fake, raising=False)
    monkeypatch.setattr(main.settings, "at_enabled", True)
    monkeypatch.setattr(main.settings, "at_api_key", "key")
    monkeypatch.setattr(main.settings, "at_sender_id", "MWALIMU")
    assert main.sms_send("+256700000001", "hello") == expected
    assert fake.calls[0]["sender_id"] == "MWALIMU"
