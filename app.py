from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from app import create_app, db
from app.models import Customer, RepairInvoice, RepairItem, RepairJob, JobCounter
from datetime import datetime
import random
import string
from sqlalchemy import or_

# Update the status constants
REPAIR_STATUSES = ['open', 'In-repair', 'Repaired', 'paid']  # all possible statuses
AVAILABLE_REPAIR_STATUSES = ['open', 'In-repair', 'Repaired']  # statuses available for selection
STATUS_COLORS = {
    'open': 'table-warning',
    'In-repair': 'table-info',
    'Repaired': 'table-success',
    'paid': 'table-secondary'
}

app = create_app()

@app.route('/')
def index():
    return redirect(url_for('view_repairs'))

@app.route('/repairs')
def view_repairs():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = RepairJob.query
    
    if search:
        query = query.join(Customer).filter(
            or_(
                Customer.name.ilike(f'%{search}%'),
                RepairJob.laptop_model.ilike(f'%{search}%'),
                RepairJob.job_number.ilike(f'%{search}%')
            )
        )
    
    pagination = query.order_by(RepairJob.created_date.desc()).paginate(
        page=page,
        per_page=10,
        error_out=False
    )
    
    return render_template('repairs.html', 
                         repairs=pagination.items,
                         pagination=pagination,
                         repair_statuses=AVAILABLE_REPAIR_STATUSES,
                         status_colors=STATUS_COLORS)

@app.route('/invoices')
def view_invoices():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = RepairInvoice.query
    
    if search:
        # Try to convert search term to float for amount search
        try:
            amount_search = float(search)
            amount_condition = RepairInvoice.total_amount == amount_search
        except ValueError:
            amount_condition = False
            
        query = query.join(RepairJob).join(Customer).filter(
            or_(
                Customer.name.ilike(f'%{search}%'),
                RepairJob.job_number.ilike(f'%{search}%'),
                amount_condition
            )
        )
    
    pagination = query.order_by(RepairInvoice.invoice_date.desc()).paginate(
        page=page,
        per_page=10,
        error_out=False
    )
    
    return render_template('invoices.html', 
                         invoices=pagination.items,
                         pagination=pagination)

@app.route('/repair/new', methods=['GET', 'POST'])
def new_repair():
    if request.method == 'POST':
        # Get current year-month
        current_ym = datetime.now().strftime("%y%m")
        
        # Get or create counter for current month
        counter = JobCounter.query.filter_by(year_month=current_ym).first()
        if not counter:
            counter = JobCounter(year_month=current_ym, last_number=0)
            db.session.add(counter)
        
        # Increment counter
        counter.last_number += 1
        
        # Create job number
        job_number = f'JOB{current_ym}{counter.last_number:03d}'
        
        # Create and commit customer first to get ID
        customer = Customer(
            name=request.form['name'],
            contact_number=request.form['contact_number'],
            email=request.form['email']
        )
        db.session.add(customer)
        db.session.commit()  # This generates the customer.id
        
        # Now create repair with valid customer_id
        repair = RepairJob(
            customer_id=customer.id,  # Now we have a valid ID
            job_number=job_number,
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
    
    if repair.status != 'Repaired':  # Case-sensitive comparison
        flash('Cannot create invoice for job that is not repaired')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Create invoice
        invoice = RepairInvoice(
            repair_job_id=repair.id,
            total_amount=request.form['total_amount'],
            status='pending'  # Set initial invoice status
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
        
        # Explicitly maintain the repair status as 'Repaired'
        repair.status = 'Repaired'  # Ensure status stays as 'Repaired'
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
    
    # Prevent changing status if repair is already paid
    if (repair.status == 'paid'):
        return jsonify({'success': False, 'message': 'Cannot modify paid repair status'}), 400
    
    # Only allow status changes to available statuses
    if new_status in AVAILABLE_REPAIR_STATUSES:
        repair.status = new_status
        db.session.commit()
        return jsonify({
            'success': True,
            'colorClass': STATUS_COLORS[new_status]
        })
    return jsonify({'success': False, 'message': 'Invalid status'}), 400

@app.route('/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = RepairInvoice.query.get_or_404(invoice_id)
    return render_template('view_invoice.html', invoice=invoice)

@app.route('/invoice/<int:invoice_id>/update', methods=['POST'])
def update_invoice(invoice_id):
    invoice = RepairInvoice.query.get_or_404(invoice_id)
    
    if invoice.status == 'paid':
        flash('Paid invoices cannot be modified')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
    
    # Update invoice date
    invoice.invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d')
    
    # Delete existing repair items
    for item in invoice.repair_items:
        db.session.delete(item)
    
    # Add new repair items
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
    
    invoice.total_amount = request.form['total_amount']
    db.session.commit()
    flash('Invoice updated successfully!')
    return redirect(url_for('view_invoice', invoice_id=invoice_id))

@app.route('/invoice/<int:invoice_id>/mark_paid', methods=['POST'])
def mark_invoice_paid(invoice_id):
    invoice = RepairInvoice.query.get_or_404(invoice_id)
    
    try:
        invoice.status = 'paid'
        invoice.repair_job.status = 'paid'  # Update repair job status to paid
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Invoice marked as paid successfully!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to mark invoice as paid'
        }), 500

@app.route('/invoice/<int:invoice_id>/delete', methods=['POST'])
def delete_invoice(invoice_id):
    invoice = RepairInvoice.query.get_or_404(invoice_id)
    if invoice.status == 'paid':
        flash('Paid invoices cannot be deleted')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
    
    db.session.delete(invoice)
    invoice.repair_job.status = 'Repaired'  # Reset repair job status
    db.session.commit()
    flash('Invoice deleted successfully!')
    return redirect(url_for('index'))

@app.route('/invoice/<int:invoice_id>/print')
def print_invoice(invoice_id):
    invoice = RepairInvoice.query.get_or_404(invoice_id)
    return render_template('print_invoice.html', invoice=invoice)

@app.route('/repair/<int:repair_id>/print')
def print_repair(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    return render_template('print_repair.html', repair=repair)

if __name__ == '__main__':
    app.run(debug=True)