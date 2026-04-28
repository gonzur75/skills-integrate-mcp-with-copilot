"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from pathlib import Path
import os
import sqlite3
import json
import secrets

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir,
          "static")), name="static")

DATABASE_PATH = current_dir / "activities.db"
TEACHERS_PATH = current_dir / "teachers.json"
TOKENS_PATH = current_dir / "tokens.json"
security = HTTPBearer()


def load_teachers():
    """Load teacher credentials from JSON file"""
    if not TEACHERS_PATH.exists():
        return {}
    with open(TEACHERS_PATH) as f:
        return json.load(f)


def initialize_teachers():
    """Create initial teachers.json with sample credentials"""
    if not TEACHERS_PATH.exists():
        teachers = {
            "mrsmith": "teacher123",
            "mschen": "instruction456"
        }
        with open(TEACHERS_PATH, 'w') as f:
            json.dump(teachers, f, indent=2)


def load_tokens():
    """Load valid session tokens"""
    if not TOKENS_PATH.exists():
        return {}
    with open(TOKENS_PATH) as f:
        return json.load(f)


def save_tokens(tokens):
    """Save valid session tokens"""
    with open(TOKENS_PATH, 'w') as f:
        json.dump(tokens, f)


def verify_teacher_token(credentials: HTTPAuthCredentials) -> str:
    """Verify teacher authentication token and return username"""
    tokens = load_tokens()
    token = credentials.credentials
    if token not in tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return tokens[token]


SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL,
            max_participants INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            activity_name TEXT NOT NULL,
            email TEXT NOT NULL,
            PRIMARY KEY(activity_name, email),
            FOREIGN KEY(activity_name) REFERENCES activities(name) ON DELETE CASCADE
        )
        """
    )

    activity_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    if activity_count == 0:
        for name, activity in SEED_ACTIVITIES.items():
            conn.execute(
                "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                (name, activity["description"], activity["schedule"], activity["max_participants"])
            )
            for email in activity["participants"]:
                conn.execute(
                    "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
                    (name, email)
                )
        conn.commit()
    conn.close()


def load_activity(activity_name: str):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT name, description, schedule, max_participants FROM activities WHERE name = ?",
        (activity_name,)
    ).fetchone()
    if row is None:
        conn.close()
        return None

    participants = [
        participant["email"]
        for participant in conn.execute(
            "SELECT email FROM participants WHERE activity_name = ? ORDER BY email",
            (activity_name,)
        ).fetchall()
    ]
    conn.close()

    return {
        "name": row["name"],
        "description": row["description"],
        "schedule": row["schedule"],
        "max_participants": row["max_participants"],
        "participants": participants,
    }


def load_activities():
    conn = get_db_connection()
    activities = {}
    activity_rows = conn.execute(
        "SELECT name, description, schedule, max_participants FROM activities ORDER BY name"
    ).fetchall()

    for row in activity_rows:
        participants = [
            participant["email"]
            for participant in conn.execute(
                "SELECT email FROM participants WHERE activity_name = ? ORDER BY email",
                (row["name"],)
            ).fetchall()
        ]
        activities[row["name"]] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants,
        }

    conn.close()
    return activities


initialize_database()
initialize_teachers()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/login")
def login(username: str, password: str):
    """Authenticate a teacher and return a session token"""
    teachers = load_teachers()
    
    if username not in teachers or teachers[username] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = secrets.token_urlsafe(32)
    tokens = load_tokens()
    tokens[token] = username
    save_tokens(tokens)
    
    return {"token": token, "username": username}


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, credentials: HTTPAuthCredentials = Depends(security)):
    """Sign up a student for an activity (teachers only)"""
    username = verify_teacher_token(credentials)
    
    activity = load_activity(activity_name)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
        (activity_name, email)
    )
    conn.commit()
    conn.close()

    return {"message": f"Signed up {email} for {activity_name}", "performed_by": username}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, credentials: HTTPAuthCredentials = Depends(security)):
    """Unregister a student from an activity (teachers only)"""
    username = verify_teacher_token(credentials)
    
    activity = load_activity(activity_name)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email)
    )
    conn.commit()
    conn.close()

    return {"message": f"Unregistered {email} from {activity_name}", "performed_by": username}
