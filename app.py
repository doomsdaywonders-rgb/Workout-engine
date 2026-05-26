import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Railway provides the PostgreSQL URL as an environment variable called DATABASE_URL.
# We fallback to a local SQLite file if you run this on your personal computer for testing.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///local_terminal.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# DATABASE SCHEMA (POSTGRESQL)
# ==========================================

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, default=datetime.utcnow().date)
    weight = db.Column(db.Float, nullable=False)
    calories_in = db.Column(db.Integer, default=0)
    protein_in = db.Column(db.Integer, default=0)
    tdee = db.Column(db.Integer, default=2500) # Baseline TDEE

class Objectives(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, default=datetime.utcnow().date)
    workout_done = db.Column(db.Boolean, default=False)
    run_5km_done = db.Column(db.Boolean, default=False)
    creatine_done = db.Column(db.Boolean, default=False)
    steps_done = db.Column(db.Boolean, default=False)

# Initialize database tables
with app.app_context():
    db.create_all()

# ==========================================
# ROUTES & LOGIC
# ==========================================

@app.route('/')
def dashboard():
    today = datetime.utcnow().date()
    
    # Fetch today's data or create empty templates if none exist
    log = DailyLog.query.filter_by(date=today).first()
    objectives = Objectives.query.filter_by(date=today).first()
    
    if not log:
        # Fallback dummy data if nothing is logged yet
        log = DailyLog(weight=88.0, calories_in=0, protein_in=0, tdee=2500)
    if not objectives:
        objectives = Objectives(workout_done=False, run_5km_done=False, creatine_done=False, steps_done=False)

    # Trajectory Forecasting Engine
    # 7700 kcal deficit = 1kg of fat loss.
    deficit = log.tdee - log.calories_in
    daily_kg_loss = deficit / 7700.0 if deficit > 0 else 0
    forecasted_weight = log.weight - daily_kg_loss

    # Calculate completed objectives out of 4
    completed_tasks = sum([objectives.workout_done, objectives.run_5km_done, objectives.creatine_done, objectives.steps_done])

    return render_template('index.html', 
                           log=log, 
                           objectives=objectives,
                           completed_tasks=completed_tasks,
                           forecasted_weight=round(forecasted_weight, 2))

@app.route('/log_data', methods=['POST'])
def log_data():
    """Endpoint to handle form submissions for new metrics."""
    today = datetime.utcnow().date()
    log = DailyLog.query.filter_by(date=today).first()
    
    if not log:
        log = DailyLog(date=today)
        db.session.add(log)
    
    # Update metrics from the frontend form
    log.weight = float(request.form.get('weight', log.weight))
    log.calories_in = int(request.form.get('calories', log.calories_in))
    log.protein_in = int(request.form.get('protein', log.protein_in))
    
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/toggle_objective/<task_name>', methods=['POST'])
def toggle_objective(task_name):
    """Endpoint to flip the boolean state of a daily objective."""
    today = datetime.utcnow().date()
    objectives = Objectives.query.filter_by(date=today).first()
    
    if not objectives:
        objectives = Objectives(date=today)
        db.session.add(objectives)

    # Flip the boolean value based on which button was pressed
    if task_name == 'workout':
        objectives.workout_done = not objectives.workout_done
    elif task_name == 'run':
        objectives.run_5km_done = not objectives.run_5km_done
    elif task_name == 'creatine':
        objectives.creatine_done = not objectives.creatine_done
    elif task_name == 'steps':
        objectives.steps_done = not objectives.steps_done

    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Railway expects apps to bind to the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
