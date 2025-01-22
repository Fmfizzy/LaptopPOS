from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from app import create_app, db
from app.models import Customer, RepairInvoice, RepairItem, RepairJob
from datetime import datetime
import random
import string

REPAIR_STATUSES = ['Open', 'In-Repair', 'Repaired', 'Paid']
STATUS_COLORS = {
    'Open': 'table-warning',
    'In-Repair': 'table-info',
    'Repaired': 'table-success',
    'Paid': 'table-secondary'
}

app = create_app()

@app.route('/')
def index():
    repairs = RepairJob.query.order_by(RepairJob.created_date.desc()).all()
    return render_template('view_all.html', 
                         repairs=repairs,
                         repair_statuses=REPAIR_STATUSES,
                         status_colors=STATUS_COLORS)

@app.route('/repair/new', methods=['GET', 'POST'])
def new_repair():
    if request.method == 'POST':
        # First create or get customer
        customer = Customer.query.filter_by(contact_number=request.form['contact_number']).first()
        if not customer:
            customer = Customer(
                name=request.form['name'],
                contact_number=request.form['contact_number'],
                email=request.form['email']
            )
            db.session.add(customer)
            db.session.commit()
        
        # Create repair job
        repair = RepairJob(
            customer_id=customer.id,
            job_number=f'JOB{datetime.now().strftime("%y%m")}{random.randint(1000,9999)}',
            laptop_model=request.form['laptop_model'],
            serial_number=request.form['serial_number'],
            hdd_status=request.form['hdd_status'],
            ram_status=request.form['ram_status'],
            battery_status=request.form['battery_status'],
            keyboard_status=request.form['keyboard_status'],
            dvd_status=request.form['dvd_status'],
            display_status=request.form['display_status'],
            power_status=request.form['power_status'],
            initial_remarks=request.form['initial_remarks']
        )
        db.session.add(repair)
        db.session.commit()
        flash('Repair job created successfully!')
        return redirect(url_for('index'))
    
    return render_template('new_repair.html')

@app.route('/repair/<int:repair_id>')
def view_repair(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    return render_template('view_repair.html', repair=repair)

@app.route('/repair/<int:repair_id>/invoice', methods=['GET', 'POST'])
def create_invoice(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    
    if repair.status != 'Repaired':
        flash('Cannot create invoice for job that is not repaired')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Create invoice
        invoice = RepairInvoice(
            repair_job_id=repair.id,
            total_amount=request.form['total_amount']
        )
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID before committing
        
        # Add repair items
        repair_types = request.form.getlist('repair_type[]')
        repair_notes = request.form.getlist('repair_note[]')
        warranty_months = request.form.getlist('warranty_months[]')
        prices = request.form.getlist('price[]')
        
        for i in range(len(repair_types)):
            item = RepairItem(
                invoice_id=invoice.id,
                repair_type=repair_types[i],
                repair_note=repair_notes[i],
                warranty_months=warranty_months[i],
                price=prices[i]
            )
            db.session.add(item)
        
        repair.status = 'invoiced'
        db.session.commit()
        flash('Invoice created successfully!')
        return redirect(url_for('index'))
    
    return render_template('create_invoice.html', 
                         repair=repair, 
                         today=datetime.now())

@app.route('/repair/<int:repair_id>/update', methods=['POST'])
def update_repair(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    
    # Update customer information
    repair.customer.name = request.form['name']
    repair.customer.contact_number = request.form['contact_number']
    repair.customer.email = request.form['email']
    
    # Update repair information
    repair.laptop_model = request.form['laptop_model']
    repair.serial_number = request.form['serial_number']
    repair.hdd_status = request.form['hdd_status']
    repair.ram_status = request.form['ram_status']
    repair.battery_status = request.form['battery_status']
    repair.keyboard_status = request.form['keyboard_status']
    repair.dvd_status = request.form['dvd_status']
    repair.display_status = request.form['display_status']
    repair.power_status = request.form['power_status']
    repair.initial_remarks = request.form['initial_remarks']
    
    db.session.commit()
    flash('Repair details updated successfully!')
    return redirect(url_for('view_repair', repair_id=repair_id))

@app.route('/repair/<int:repair_id>/delete', methods=['POST'])
def delete_repair(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    db.session.delete(repair)
    db.session.commit()
    flash('Repair record deleted successfully!')
    return redirect(url_for('index'))

@app.route('/repair/<int:repair_id>/status', methods=['POST'])
def update_status(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    new_status = request.form.get('status')
    if new_status in REPAIR_STATUSES:
        repair.status = new_status
        db.session.commit()
        return jsonify({
            'success': True,
            'colorClass': STATUS_COLORS[new_status]
        })
    return jsonify({'success': False}), 400

if __name__ == '__main__':
    app.run(debug=True)