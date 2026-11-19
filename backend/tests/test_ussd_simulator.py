import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app import main


def seed_test_data(db):
    teacher = main.Teacher(name="Test teacher", email="teacher@test.local", password_hash="test")
    db.add(teacher)
    db.flush()
    classroom = main.SchoolClass(teacher_id=teacher.id, name="Test class", subject="Science")
    db.add(classroom)
    db.flush()
    student = main.Student(
        class_id=classroom.id,
        student_code="001",
        name="Test learner",
        phone_number="+256700000001",
    )
    misconception = main.Misconception(
        name="Test misconception",
        description="Test description",
        topic="Test topic",
        intervention="Test intervention",
    )
    db.add_all([student, misconception])
    db.flush()

    questions = [
        main.Question(class_id=classroom.id, text="Question one?", topic="One"),
        main.Question(class_id=classroom.id, text="Question two?", topic="Two"),
        main.Question(class_id=classroom.id, text="Question three?", topic="Three"),
    ]
    db.add_all(questions)
    db.flush()
    for index, question in enumerate(questions):
        wrong_misconception = misconception.id if index in (0, 2) else None
        db.add_all([
            main.Option(
                question_id=question.id,
                label="A",
                text="Wrong answer",
                is_correct=False if index != 1 else True,
                misconception_id=wrong_misconception,
            ),
            main.Option(
                question_id=question.id,
                label="B",
                text="Correct answer",
                is_correct=True if index != 1 else False,
            ),
        ])
    assessment = main.Assessment(class_id=classroom.id, title="Test baseline", kind="baseline")
    db.add(assessment)
    db.flush()
    for position, question in enumerate(questions):
        db.add(main.AssessmentQuestion(assessment_id=assessment.id, question_id=question.id, position=position))
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
        monkeypatch.setattr(main, "seed", seed_test_data)
        yield TestSession
        engine.dispose()


def test_simulated_ussd_quiz_and_sms_inbox(isolated_database):
    TestSession = isolated_database

    with TestClient(main.app) as client:
        session_id = "simulator-session-one"
        phone = "+256700000001"

        def send(text):
            return client.post(
                "/api/ussd/callback",
                data={
                    "sessionId": session_id,
                    "serviceCode": "*123#",
                    "phoneNumber": phone,
                    "text": text,
                },
                headers={"X-Mwalimu-Simulator": "true"},
            ).json()

        assert send("").startswith("CON Welcome to Mwalimu")
        assert send("1").startswith("CON Enter your learner ID")
        assert send("1*001").startswith("CON Q1:")
        assert send("1*001*9").startswith("CON Invalid selection")
        assert send("1*001*9*1").startswith("CON Q2:")
        assert send("1*001*9*1*1").startswith("CON Q3:")
        assert send("1*001*9*1*1*1").startswith("END Quiz complete! Score: 1/3")

        auth = {"Authorization": "Bearer radar-demo-token"}
        inbox = client.get(
            "/api/ussd/messages", params={"phoneNumber": phone}, headers=auth
        )
        assert inbox.status_code == 200
        messages = inbox.json()
        assert len(messages) == 2
        assert all(message["recipient"] == phone for message in messages)
        assert all(message["delivery_status"] == "demo" for message in messages)
        assert all("MWALIMU" in message["message"] for message in messages)

        with TestSession() as db:
            attempt = db.query(main.Attempt).one()
            responses = db.query(main.Response).filter_by(attempt_id=attempt.id).all()
            assert attempt.completed is True
            assert attempt.score == 1 and attempt.total == 3
            assert len(responses) == 3
            assert any(response.misconception_id for response in responses)

        second_id = "simulator-session-two"
        started = client.post(
            "/api/ussd/callback",
            data={"sessionId": second_id, "serviceCode": "*123#", "phoneNumber": phone, "text": ""},
        )
        assert started.json().startswith("CON Welcome to Mwalimu")
        ended = client.post(
            "/api/ussd/callback",
            data={"sessionId": second_id, "serviceCode": "*123#", "phoneNumber": phone, "text": "9"},
        )
        assert ended.json().startswith("END Invalid choice")

        third_id = "simulator-session-three"
        client.post(
            "/api/ussd/callback",
            data={"sessionId": third_id, "serviceCode": "*123#", "phoneNumber": phone, "text": ""},
        )
        client.post(
            "/api/ussd/callback",
            data={"sessionId": third_id, "serviceCode": "*123#", "phoneNumber": phone, "text": "1"},
        )
        stopped = client.post(
            "/api/ussd/callback",
            data={"sessionId": third_id, "serviceCode": "*123#", "phoneNumber": phone, "text": "1*0"},
        )
        assert stopped.json().startswith("END Session ended")

