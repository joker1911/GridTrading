from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class InStock(db.Model):
    __tablename__ = 'in_stock'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    buyQuantity = db.Column(db.Float, nullable=True)
    soldQuantity = db.Column(db.Float, nullable=True)
    buyPrice = db.Column(db.Float, nullable=True)
    sellPrice = db.Column(db.Float, nullable=True)
    buyDate = db.Column(db.DateTime, nullable=True)
    sellDate = db.Column(db.DateTime, nullable=True)
    cash = db.Column(db.Float, nullable=True)
    total = db.Column(db.Float, nullable=False)

class TodayStock(db.Model):
    __tablename__ = 'today_stock'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)