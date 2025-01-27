# app/models.py
from app import db
from datetime import datetime

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    repair_jobs = db.relationship('RepairJob', backref='customer', lazy=True)
    quotations = db.relationship('Quotation', backref='customer', lazy=True)

class RepairJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    job_number = db.Column(db.String(20), unique=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    laptop_model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    status = db.Column(db.String(20), default='open')  # open, in-repair, repaired, completed
    
    # Status checks
    hdd_status = db.Column(db.String(50))
    ram_status = db.Column(db.String(50))
    battery_status = db.Column(db.String(50))
    keyboard_status = db.Column(db.String(50))
    dvd_status = db.Column(db.String(50))
    display_status = db.Column(db.String(50))
    power_status = db.Column(db.String(50))
    
    initial_remarks = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)
    invoices = db.relationship('RepairInvoice', backref='repair_job', lazy=True)

class RepairInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repair_job_id = db.Column(db.Integer, db.ForeignKey('repair_job.id'), nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='pending')  # pending, paid
    repair_items = db.relationship('RepairItem', backref='invoice', lazy=True,
                                 cascade='all, delete-orphan')

class RepairItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('repair_invoice.id', ondelete='CASCADE'))
    repair_type = db.Column(db.String(100))
    repair_note = db.Column(db.Text)
    warranty_months = db.Column(db.Integer)
    price = db.Column(db.Numeric(10, 2))

class Quotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    quotation_number = db.Column(db.String(20), unique=True, nullable=False)
    quotation_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='open')  # open, paid
    total_amount = db.Column(db.Numeric(10, 2))
    items = db.relationship('QuotationItem', backref='quotation', lazy=True)

class QuotationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'), nullable=False)
    item_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Numeric(10, 2))
    total_price = db.Column(db.Numeric(10, 2))