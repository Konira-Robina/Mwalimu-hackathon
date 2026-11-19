from datetime import datetime, timezone
from uuid import uuid4
import json, logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Boolean, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
from passlib.context import CryptContext
from pydantic_settings import BaseSettings, SettingsConfigDict
import httpx

class Settings(BaseSettings):
    database_url: str = "sqlite:///./radar.db"
    frontend_origin: str = "http://localhost:3000"
    at_username: str = "sandbox"
    at_api_key: str = ""
    at_enabled: bool = False
    at_sender_id: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread":False} if settings.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase): pass
def now(): return datetime.now(timezone.utc)

class Teacher(Base):
    __tablename__="teachers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    name:Mapped[str]=mapped_column(String(120)); email:Mapped[str]=mapped_column(String(180),unique=True)
    password_hash:Mapped[str]=mapped_column(String(255))
class SchoolClass(Base):
    __tablename__="classes"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    teacher_id:Mapped[str]=mapped_column(ForeignKey("teachers.id")); name:Mapped[str]=mapped_column(String(120)); subject:Mapped[str]=mapped_column(String(80))
class Student(Base):
    __tablename__="students"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    class_id:Mapped[str]=mapped_column(ForeignKey("classes.id"),index=True)
    student_code:Mapped[str]=mapped_column(String(30),index=True); name:Mapped[str]=mapped_column(String(120)); phone_number:Mapped[str]=mapped_column(String(30))
class Misconception(Base):
    __tablename__="misconceptions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    name:Mapped[str]=mapped_column(String(180),unique=True); description:Mapped[str]=mapped_column(Text)
    topic:Mapped[str]=mapped_column(String(100)); intervention:Mapped[str]=mapped_column(Text)
class Question(Base):
    __tablename__="questions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    class_id:Mapped[str]=mapped_column(ForeignKey("classes.id")); text:Mapped[str]=mapped_column(Text)
    topic:Mapped[str]=mapped_column(String(100)); explanation:Mapped[str]=mapped_column(Text,default="")
    options:Mapped[list["Option"]]=relationship(back_populates="question",cascade="all, delete-orphan")
class Option(Base):
    __tablename__="answer_options"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    question_id:Mapped[str]=mapped_column(ForeignKey("questions.id"),index=True)
    label:Mapped[str]=mapped_column(String(2)); text:Mapped[str]=mapped_column(Text)
    is_correct:Mapped[bool]=mapped_column(Boolean,default=False)
    misconception_id:Mapped[Optional[str]]=mapped_column(ForeignKey("misconceptions.id"),nullable=True)
    feedback:Mapped[str]=mapped_column(Text,default="")
    question:Mapped[Question]=relationship(back_populates="options")
    misconception:Mapped[Optional[Misconception]]=relationship()
class Assessment(Base):
    __tablename__="assessments"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    class_id:Mapped[str]=mapped_column(ForeignKey("classes.id")); title:Mapped[str]=mapped_column(String(180))
    kind:Mapped[str]=mapped_column(String(20)); questions:Mapped[list["AssessmentQuestion"]]=relationship(cascade="all, delete-orphan")
class AssessmentQuestion(Base):
    __tablename__="assessment_questions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    assessment_id:Mapped[str]=mapped_column(ForeignKey("assessments.id"),index=True)
    question_id:Mapped[str]=mapped_column(ForeignKey("questions.id")); position:Mapped[int]=mapped_column(Integer,default=0)
class Attempt(Base):
    __tablename__="quiz_attempts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    assessment_id:Mapped[str]=mapped_column(ForeignKey("assessments.id"),index=True)
    student_id:Mapped[str]=mapped_column(ForeignKey("students.id"),index=True)
    score:Mapped[int]=mapped_column(Integer,default=0); total:Mapped[int]=mapped_column(Integer,default=0)
    completed:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Response(Base):
    __tablename__="student_responses"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    attempt_id:Mapped[str]=mapped_column(ForeignKey("quiz_attempts.id"),index=True)
    question_id:Mapped[str]=mapped_column(ForeignKey("questions.id"))
    option_id:Mapped[str]=mapped_column(ForeignKey("answer_options.id"))
    correct:Mapped[bool]=mapped_column(Boolean); misconception_id:Mapped[Optional[str]]=mapped_column(ForeignKey("misconceptions.id"),nullable=True)
    sms_status:Mapped[str]=mapped_column(String(20),default="not_needed")
class UssdSession(Base):
    __tablename__="ussd_sessions"
    session_id:Mapped[str]=mapped_column(String(120),primary_key=True)
    phone:Mapped[str]=mapped_column(String(30)); student_id:Mapped[Optional[str]]=mapped_column(ForeignKey("students.id"),nullable=True)
    assessment_id:Mapped[Optional[str]]=mapped_column(ForeignKey("assessments.id"),nullable=True)
    attempt_id:Mapped[Optional[str]]=mapped_column(ForeignKey("quiz_attempts.id"),nullable=True)

class SmsMessage(Base):
    __tablename__="sms_messages"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    recipient:Mapped[str]=mapped_column(String(30),index=True)
    message:Mapped[str]=mapped_column(Text)
    delivery_status:Mapped[str]=mapped_column(String(20),default="demo")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

Base.metadata.create_all(engine)
def db_dep():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def sms_send(phone,message,force_demo=False):
    if force_demo:
        logging.info("SIMULATOR DEMO SMS to %s: %s",phone,message); return "demo"
    if not settings.at_enabled or not settings.at_api_key:
        logging.info("DEMO SMS to %s: %s",phone,message); return "demo"
    try:
        import africastalking
        africastalking.initialize(settings.at_username,settings.at_api_key)
        kwargs={"from_":settings.at_sender_id} if settings.at_sender_id else {}
        result=africastalking.SMS.send(message,[phone],**kwargs)
        logging.info("AT SMS response: %s",result); return "accepted"
    except Exception:
        logging.exception("SMS failed"); return "failed"

async def generate_learning_explanation(question: str, correct_answer: str, selected_answer: str, misconception: str, teacher_feedback: str = "") -> str:
    """Generate a short learner-friendly explanation; fall back to teacher-authored feedback."""
    fallback = teacher_feedback.strip() or f"The correct answer is: {correct_answer}. Review this idea and try again."
    if not settings.openrouter_api_key:
        return fallback
    prompt = (
        "You are a kind, clear secondary-school science tutor. Explain the learner's likely misconception "
        "in simple language suitable for an SMS. Do not shame the learner. Do not diagnose beyond the "
        "provided misconception. Give one short correction and, if useful, one simple example. "
        "Return plain text only, maximum 320 characters.\n\n"
        f"Question: {question}\nLearner selected: {selected_answer}\n"
        f"Correct answer: {correct_answer}\nMisconception to address: {misconception}\n"
        f"Teacher guidance: {teacher_feedback or 'None provided'}"
    )
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Mwalimu",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [
                        {"role": "system", "content": "You are an encouraging educational tutor."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 130,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                return content.strip()[:500]
    except Exception:
        logging.exception("OpenRouter explanation generation failed; using teacher-authored feedback")
    return fallback

def seed(db):
    if db.query(Teacher).first(): return
    t=Teacher(name="Sarah Namusoke",email="teacher@demo.com",password_hash=pwd.hash("RadarDemo123!")); db.add(t); db.flush()
    c=SchoolClass(teacher_id=t.id,name="Senior 2 Science",subject="Science"); db.add(c); db.flush()
    learners=[]
    for i in range(1,31):
        s=Student(class_id=c.id,student_code=f"{i:03}",name=f"Student {i:02}",phone_number=f"+256700000{i:03}");db.add(s);learners.append(s)
    m1=Misconception(name="Evaporation makes water disappear",description="The learner may think water ceases to exist during evaporation.",topic="States of Matter",intervention="Use a covered and uncovered container to explain water vapour and conservation of matter.")
    m2=Misconception(name="Melting creates a new substance",description="The learner may confuse a change of state with a chemical change.",topic="States of Matter",intervention="Melt ice and compare the resulting liquid with the original water.")
    m3=Misconception(name="Freezing destroys water",description="The learner may think freezing removes or destroys water.",topic="States of Matter",intervention="Freeze a measured amount of water and discuss the change of state.")
    db.add_all([m1,m2,m3]);db.flush()
    raw=[
    ("What happens during evaporation?","Evaporation",[("A","Water turns into ice",False,m2,"Evaporation is different from freezing. Water changes from liquid into water vapour."),("B","Water changes into water vapour",True,None,""),("C","Water disappears completely",False,m1,"Water does not disappear. It changes into water vapour that mixes with the air.")]),
    ("What happens when ice melts?","Melting",[("A","Solid water changes into liquid water",True,None,""),("B","Water becomes a different substance",False,m2,"Melting is a physical change of state. The substance remains water."),("C","Water is destroyed",False,m3,"Water is not destroyed when ice melts; it changes from solid to liquid.")]),
    ("What happens when liquid water freezes?","Freezing",[("A","It changes into water vapour",False,m1,"Freezing changes liquid water into solid ice, not water vapour."),("B","It changes into solid ice",True,None,""),("C","The water is destroyed",False,m3,"Freezing does not destroy water. It changes liquid water into a solid.")])]
    qs=[]
    for text,topic,opts in raw:
        q=Question(class_id=c.id,text=text,topic=topic,explanation="A change of state changes the form of water, not the substance.");db.add(q);db.flush()
        for label,txt,correct,mc,fb in opts: db.add(Option(question_id=q.id,label=label,text=txt,is_correct=correct,misconception_id=mc.id if mc else None,feedback=fb))
        qs.append(q)
    db.flush()
    base=Assessment(class_id=c.id,title="States of Matter – Baseline",kind="baseline")
    follow=Assessment(class_id=c.id,title="States of Matter – Follow-up",kind="followup");db.add_all([base,follow]);db.flush()
    for i,q in enumerate(qs):
        db.add(AssessmentQuestion(assessment_id=base.id,question_id=q.id,position=i));db.add(AssessmentQuestion(assessment_id=follow.id,question_id=q.id,position=i))
    db.flush()
    for i,s in enumerate(learners):
        for assessment,kind in [(base,"baseline"),(follow,"followup")]:
            attempt=Attempt(assessment_id=assessment.id,student_id=s.id,total=3,completed=True,score=0);db.add(attempt);db.flush()
            for qi,q in enumerate(qs):
                opts=db.query(Option).filter_by(question_id=q.id).all()
                if qi==0 and kind=="baseline" and i<18: selected=next(o for o in opts if o.misconception_id==m1.id)
                elif qi==0 and kind=="followup" and 15<=i<18: selected=next(o for o in opts if o.misconception_id==m1.id)
                else: selected=next(o for o in opts if o.is_correct)
                db.add(Response(attempt_id=attempt.id,question_id=q.id,option_id=selected.id,correct=selected.is_correct,misconception_id=selected.misconception_id,sms_status="demo" if not selected.is_correct else "not_needed"))
                if selected.is_correct: attempt.score+=1
    db.commit()

app=FastAPI(title="Mwalimu | Understand. Teach. Improve.",version="1.0.0",description="An AI-powered learning recovery platform that helps teachers identify learner misconceptions, provide personalised feedback, and measure learning progress.")
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin,"http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def startup():
    d=SessionLocal()
    try: seed(d)
    finally: d.close()

def auth(authorization:Optional[str]=Header(default=None)):
    if authorization!="Bearer radar-demo-token": raise HTTPException(401,"Please sign in.")
@app.get("/health")
def health(): return {"status":"ok"}

class ExplanationIn(BaseModel):
    question: str
    correct_answer: str
    selected_answer: str
    misconception: str
    teacher_feedback: str = ""

@app.post("/api/ai/explanation", dependencies=[Depends(auth)])
async def ai_explanation(x: ExplanationIn):
    explanation = await generate_learning_explanation(
        x.question, x.correct_answer, x.selected_answer, x.misconception, x.teacher_feedback
    )
    return {
        "explanation": explanation,
        "provider": "openrouter" if settings.openrouter_api_key else "teacher_fallback",
        "model": settings.openrouter_model if settings.openrouter_api_key else None,
    }
class Login(BaseModel): email:str; password:str
@app.post("/api/auth/login")
def login(x:Login,db:Session=Depends(db_dep)):
    t=db.query(Teacher).filter(func.lower(Teacher.email)==x.email.lower()).first()
    if not t or not pwd.verify(x.password,t.password_hash): raise HTTPException(401,"Invalid email or password.")
    return {"access_token":"radar-demo-token","teacher":{"name":t.name,"email":t.email}}
@app.get("/api/dashboard/overview",dependencies=[Depends(auth)])
def overview(db:Session=Depends(db_dep)):
    responses=db.query(Response).all(); total=len(responses); correct=sum(r.correct for r in responses)
    mc=db.query(Misconception).filter_by(name="Evaporation makes water disappear").first()
    baseline=db.query(Response,Attempt).join(Attempt).join(Assessment).filter(Assessment.kind=="baseline",Response.misconception_id==mc.id).all()
    ids={a.student_id for _,a in baseline}; recovered=0
    for sid in ids:
        still=db.query(Response).join(Attempt).join(Assessment).filter(Assessment.kind=="followup",Attempt.student_id==sid,Response.misconception_id==mc.id).count()
        if not still: recovered+=1
    return {"total_students":db.query(Student).count(),"assessments_completed":db.query(Attempt).filter_by(completed=True).count(),"average_score":round(correct/total*100,1) if total else 0,"misconceptions_detected":db.query(Misconception).count(),"recovery_rate":round(recovered/len(ids)*100,1) if ids else 0,"recovery_recovered":recovered,"recovery_eligible":len(ids),"dataset_label":"Illustrative demo data"}
@app.get("/api/classes",dependencies=[Depends(auth)])
def classes(db:Session=Depends(db_dep)):
    return [{"id":c.id,"name":c.name,"subject":c.subject,"student_count":db.query(Student).filter_by(class_id=c.id).count()} for c in db.query(SchoolClass).all()]
@app.get("/api/students",dependencies=[Depends(auth)])
def students(db:Session=Depends(db_dep)):
    return [{"id":s.id,"student_code":s.student_code,"name":s.name,"phone_number":s.phone_number,"class_id":s.class_id} for s in db.query(Student).order_by(Student.student_code).all()]
@app.get("/api/students/{student_id}/results", dependencies=[Depends(auth)])
def student_results(student_id: str, db: Session = Depends(db_dep)):
    student = db.get(Student, student_id)

    if not student:
        raise HTTPException(404, "Learner not found.")

    attempts = (
        db.query(Attempt, Assessment)
        .join(Assessment, Attempt.assessment_id == Assessment.id)
        .filter(Attempt.student_id == student_id)
        .order_by(Attempt.created_at.desc())
        .all()
    )

    results = []

    for attempt, assessment in attempts:
        responses = (
            db.query(Response, Question, Option, Misconception)
            .join(Question, Response.question_id == Question.id)
            .join(Option, Response.option_id == Option.id)
            .outerjoin(Misconception, Response.misconception_id == Misconception.id)
            .filter(Response.attempt_id == attempt.id)
            .all()
        )

        results.append({
            "attempt_id": attempt.id,
            "assessment_title": assessment.title,
            "assessment_type": assessment.kind,
            "score": attempt.score,
            "total": attempt.total,
            "completed": attempt.completed,
            "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
            "responses": [
                {
                    "question": question.text,
                    "topic": question.topic,
                    "selected_answer": option.text,
                    "correct": response.correct,
                    "misconception": misconception.name if misconception else None,
                }
                for response, question, option, misconception in responses
            ],
        })

    return {
        "student": {
            "id": student.id,
            "student_code": student.student_code,
            "name": student.name,
            "phone_number": student.phone_number,
        },
        "attempts": results,
    }
class StudentIn(BaseModel): class_id:str; student_code:str; name:str; phone_number:str
@app.post("/api/students",dependencies=[Depends(auth)])
def add_student(x:StudentIn,db:Session=Depends(db_dep)):
    s=Student(**x.model_dump());db.add(s)
    try: db.commit()
    except Exception: db.rollback();raise HTTPException(409,"Student code already exists.")
    return {"id":s.id,"name":s.name}
class ClassIn(BaseModel): name:str; subject:str="Science"
@app.post("/api/classes",dependencies=[Depends(auth)])
def add_class(x:ClassIn,db:Session=Depends(db_dep)):
    t=db.query(Teacher).first();c=SchoolClass(teacher_id=t.id,name=x.name,subject=x.subject);db.add(c);db.commit();return {"id":c.id,"name":c.name,"subject":c.subject,"student_count":0}
def q_json(q):
    return {"id":q.id,"text":q.text,"topic":q.topic,"options":[{"id":o.id,"label":o.label,"text":o.text,"is_correct":o.is_correct,"misconception":o.misconception.name if o.misconception else None,"feedback":o.feedback} for o in q.options]}
@app.get("/api/questions",dependencies=[Depends(auth)])
def questions(db:Session=Depends(db_dep)): return [q_json(q) for q in db.query(Question).all()]
class OptIn(BaseModel):
    label:str; text:str; is_correct:bool=False; misconception_name:Optional[str]=None; feedback:str=""
class QuestionIn(BaseModel):
    class_id:str; text:str; topic:str; options:list[OptIn]
@app.post("/api/questions",dependencies=[Depends(auth)])
def add_question(x:QuestionIn,db:Session=Depends(db_dep)):
    if len(x.options)<2 or sum(o.is_correct for o in x.options)!=1: raise HTTPException(400,"Provide at least two options and exactly one correct answer.")
    q=Question(class_id=x.class_id,text=x.text,topic=x.topic);db.add(q);db.flush()
    for o in x.options:
        mc=None
        if not o.is_correct and o.misconception_name:
            mc=db.query(Misconception).filter_by(name=o.misconception_name).first()
            if not mc: mc=Misconception(name=o.misconception_name,description=o.misconception_name,topic=x.topic,intervention="Review this concept with the class.");db.add(mc);db.flush()
        db.add(Option(question_id=q.id,label=o.label,text=o.text,is_correct=o.is_correct,misconception_id=mc.id if mc else None,feedback=o.feedback))
    db.commit();db.refresh(q);return q_json(q)
@app.get("/api/analytics/misconceptions",dependencies=[Depends(auth)])
def misconceptions(db:Session=Depends(db_dep)):
    out=[]
    for m in db.query(Misconception).all():
        rows=db.query(Response,Attempt).join(Attempt).filter(Response.misconception_id==m.id).all()
        out.append({"id":m.id,"name":m.name,"topic":m.topic,"affected_students":len({a.student_id for _,a in rows}),"response_count":len(rows),"description":m.description,"intervention":m.intervention})
    return sorted(out,key=lambda x:x["affected_students"],reverse=True)
@app.get("/api/analytics/recovery",dependencies=[Depends(auth)])
def recovery(db:Session=Depends(db_dep)):
    out=[]
    for m in db.query(Misconception).all():
        base=db.query(Response,Attempt).join(Attempt).join(Assessment).filter(Assessment.kind=="baseline",Response.misconception_id==m.id).all()
        ids={a.student_id for _,a in base}; got=0
        for sid in ids:
            still=db.query(Response).join(Attempt).join(Assessment).filter(Assessment.kind=="followup",Attempt.student_id==sid,Response.misconception_id==m.id).count()
            if not still: got+=1
        out.append({"misconception":m.name,"eligible":len(ids),"recovered":got,"rate":round(got/len(ids)*100,1) if ids else 0})
    return {"items":out}
@app.get("/api/assessments",dependencies=[Depends(auth)])
def assessments(db:Session=Depends(db_dep)):
    return [{"id":a.id,"title":a.title,"type":a.kind,"question_count":len(a.questions),"published":True} for a in db.query(Assessment).all()]
@app.get("/api/ussd/status")
def ussd_status(): return {"configured":settings.at_enabled and bool(settings.at_api_key),"mode":"sandbox" if settings.at_username=="sandbox" else "live"}
@app.get("/api/ussd/messages",dependencies=[Depends(auth)])
def ussd_messages(phoneNumber:Optional[str]=None,db:Session=Depends(db_dep)):
    query=db.query(SmsMessage)
    if phoneNumber:
        query=query.filter(SmsMessage.recipient==phoneNumber)
    rows=query.order_by(SmsMessage.created_at.desc()).limit(100).all()
    return [{"id":row.id,"recipient":row.recipient,"message":row.message,"delivery_status":row.delivery_status,"created_at":row.created_at.isoformat() if row.created_at else None} for row in rows]
def assessment_questions(db,a):
    links=db.query(AssessmentQuestion).filter_by(assessment_id=a.id).order_by(AssessmentQuestion.position).all()
    return [db.get(Question,l.question_id) for l in links]
@app.post("/api/ussd/callback")
async def ussd_callback(sessionId:str=Form(...),serviceCode:str=Form(""),phoneNumber:str=Form(...),text:str=Form(""),simulator:bool=Header(default=False,alias="X-Mwalimu-Simulator")):
    db=SessionLocal()
    try:
        parts=text.split("*") if text else []; sess=db.get(UssdSession,sessionId)
        if not sess: sess=UssdSession(session_id=sessionId,phone=phoneNumber);db.add(sess);db.commit()
        if not parts: return "CON Welcome to Mwalimu\\nUnderstand. Teach. Improve.\\n1. Start quiz\\n2. Exit"
        if parts[-1]=="0":
            db.delete(sess);db.commit();return "END Session ended. Thank you for learning."
        if parts[0]=="2": db.delete(sess);db.commit();return "END Thank you for learning."
        if parts[0]!="1": db.delete(sess);db.commit();return "END Invalid choice. Please dial again."
        if len(parts)==1: return "CON Enter your learner ID (example: 001):"
        if len(parts)==2:
            learner=db.query(Student).filter_by(student_code=parts[1]).first()
            if not learner:return "END Learner ID not found. Ask your teacher to register you."
            a=db.query(Assessment).filter_by(class_id=learner.class_id,kind="baseline").first()
            if not a:return "END No active quiz for your class."
            attempt=Attempt(assessment_id=a.id,student_id=learner.id,total=len(a.questions));db.add(attempt);db.flush()
            sess.student_id=learner.id;sess.assessment_id=a.id;sess.attempt_id=attempt.id;db.commit()
            q=assessment_questions(db,a)[0];opts=sorted(q.options,key=lambda o:o.label)
            return "CON Q1: "+q.text+"\\n"+"\\n".join(f"{i+1}. {o.text}" for i,o in enumerate(opts))
        learner=db.get(Student,sess.student_id) if sess.student_id else None;a=db.get(Assessment,sess.assessment_id) if sess.assessment_id else None;attempt=db.get(Attempt,sess.attempt_id) if sess.attempt_id else None
        if not learner or not a or not attempt:return "END Session expired. Please dial again."
        qs=assessment_questions(db,a);q_index=db.query(Response).filter_by(attempt_id=attempt.id).count()
        if q_index<0 or q_index>=len(qs):return "END Quiz already completed."
        q=qs[q_index];opts=sorted(q.options,key=lambda o:o.label);choice=parts[-1]
        if not choice.isdigit() or int(choice)<1 or int(choice)>len(opts):return "CON Invalid selection. Enter a valid option number."
        selected=opts[int(choice)-1]
        if not db.query(Response).filter_by(attempt_id=attempt.id,question_id=q.id).first():
            db.add(Response(attempt_id=attempt.id,question_id=q.id,option_id=selected.id,correct=selected.is_correct,misconception_id=selected.misconception_id))
            if selected.is_correct:attempt.score+=1
            else:
                correct_option=next((o for o in opts if o.is_correct), None)
                misconception_name=selected.misconception.name if selected.misconception else "Review the concept"
                explanation=await generate_learning_explanation(
                    q.text, correct_option.text if correct_option else "the correct concept",
                    selected.text, misconception_name, selected.feedback
                )
                msg=f"MWALIMU\\nYou selected: {selected.text}\\n\\n{explanation}\\n\\nKeep learning!"
                force_demo=simulator and settings.at_username!="sandbox"
                status=sms_send(learner.phone_number,msg,force_demo=force_demo)
                recorded_status="sandbox_accepted" if status=="accepted" and settings.at_username=="sandbox" else status
                db.add(SmsMessage(recipient=learner.phone_number,message=msg,delivery_status=recorded_status));db.flush()
                r=db.query(Response).filter_by(attempt_id=attempt.id,question_id=q.id).first()
                if r:r.sms_status=status
        next_i=q_index+1
        if next_i>=len(qs):
            attempt.completed=True;db.commit();db.delete(sess);db.commit()
            return f"END Quiz complete! Score: {attempt.score}/{attempt.total}. Check your SMS feedback."
        db.commit();nq=qs[next_i];no=sorted(nq.options,key=lambda o:o.label)
        return "CON "+f"Q{next_i+1}: {nq.text}\\n"+"\\n".join(f"{i+1}. {o.text}" for i,o in enumerate(no))
    except Exception:
        db.rollback();logging.exception("USSD callback failure");return "END Sorry, something went wrong. Please try again."
    finally:db.close()
@app.get("/")
def root():return {"app":"Mwalimu","docs":"/docs"}
