from extensions import db
from flask_login import UserMixin
from datetime import datetime 

# USER_MODEL
class User(UserMixin,db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(100), nullable=False)
    email=db.Column(db.String(120), unique=True, nullable=False)
    password=db.Column(db.String(255),nullable=False)
    phone=db.Column(db.String(20))
    role=db.Column(db.String(20),nullable=False)
    status=db.Column(db.String(20), default='pending')
    created_at=db.Column(db.DateTime, default=datetime.utcnow)
    bookings=db.relationship('Booking', backref='user',lazy=True)
    assigned_treks=db.relationship('Trek',backref='staff',lazy=True)


# TREK_MODEL
class Trek(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    trek_name=db.Column(db.String(100),nullable=False)
    location=db.Column(db.String(100),nullable=False)
    difficulty=db.Column(db.String(20))
    duration=db.Column(db.Integer)
    available_slots=db.Column(db.Integer, default=0)
    start_date=db.Column(db.Date)
    end_date=db.Column(db.Date)
    status=db.Column(db.String(20),default='open')
    description=db.Column(db.Text)
    assigned_staff_id=db.Column(db.Integer,db.ForeignKey('user.id'))
    bookings=db.relationship('Booking',backref='trek',lazy=True)
    image=db.Column(db.String(200),nullable=True)

# BOOKING_MODEL
class Booking(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'))
    trek_id=db.Column(db.Integer,db.ForeignKey('trek.id'))
    booking_date=db.Column(db.DateTime,default=datetime.utcnow)
    status=db.Column(db.String(20),default='booked')