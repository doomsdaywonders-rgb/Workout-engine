from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os

app = Flask(__name__)

# Railway Database Connection with Modern psycopg driver
db_url = os.environ.get('DATABASE_URL', 'sqlite:///local_terminal.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Architecture
class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, default=date.today)
    weight = db.Column(db.Float, default=88.0)
    calories_in = db.Column(db.Integer, default=0)
    protein_in = db.Column(db.Integer, default=0)
    
    # Binary Execution Objectives
    workout_done = db.Column(db.Boolean, default=False)
    run_done = db.Column(db.Boolean, default=False)
    creatine_done = db.Column(db.Boolean, default=False)
    steps_done = db.Column(db.Boolean, default=False)

# Initialize Database
with app.app_context():
    # UNCOMMENT THE LINE BELOW FOR EXACTLY 1 DEPLOYMENT TO FIX THE DATABASE ERROR
    # db.drop_all() 
    db.create_all()

@app.route('/')
def index():
    today = date.today()
    log = DailyLog.query.filter_by(date=today).first()
    
    # Create a fresh log for the day if it doesn't exist
    if not log:
        # Carry over yesterday's weight if possible
        last_log = DailyLog.query.order_by(DailyLog.date.desc()).first()
        start_weight = last_log.weight if last_log else 88.0
        log = DailyLog(date=today, weight=start_weight)
        db.session.add(log)
        db.session.commit()

    # --- THE CLOSED-LOOP TRAJECTORY MATH ---
    base_tdee = 2500
    active_burn = 0
    
    # Add active burn based on UI checkboxes
    if log.workout_done:
        active_burn += 300
    if log.run_done:
        active_burn += 400
        
    total_tdee = base_tdee + active_burn

    # Calculate biological fat loss forecast
    # If no calories are logged yet, assume maintenance to prevent wild chart swings
    effective_calories = log.calories_in if log.calories_in > 0 else total_tdee
    deficit = total_tdee - effective_calories
    
    # 7700 kcal deficit = 1kg fat loss
    fat_loss_kg = deficit / 7700
    forecasted_weight = round(log.weight - fat_loss_kg, 2)

    # UI Counter
    completed_tasks = sum([log.workout_done, log.run_done, log.creatine_done, log.steps_done])

    return render_template('index.html', log=log, tdee=total_tdee, forecasted_weight=forecasted_weight, completed_tasks=completed_tasks)


@app.route('/log_data', methods=['POST'])
def log_data():
    log = DailyLog.query.filter_by(date=date.today()).first()
    log.weight = float(request.form.get('weight', log.weight))
    log.calories_in = int(request.form.get('calories', log.calories_in))
    log.protein_in = int(request.form.get('protein', log.protein_in))
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/toggle/<task>', methods=['POST'])
def toggle(task):
    log = DailyLog.query.filter_by(date=date.today()).first()
    if task == 'workout': log.workout_done = not log.workout_done
    elif task == 'run': log.run_done = not log.run_done
    elif task == 'creatine': log.creatine_done = not log.creatine_done
    elif task == 'steps': log.steps_done = not log.steps_done
    db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
