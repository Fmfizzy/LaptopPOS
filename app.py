import os
import sys
import time
import random
import string
import logging
import threading
import webbrowser
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from sqlalchemy import or_
from app import create_app, db
from app.models import Customer, RepairInvoice, RepairItem, RepairJob, JobCounter, Sale, ManualEntry

# Update the status constants
REPAIR_STATUSES = ['open', 'In-repair', 'Repaired', 'paid', "can't-repair"]  # all possible statuses
AVAILABLE_REPAIR_STATUSES = ['open', 'In-repair', 'Repaired', "can't-repair"]  # statuses available for selection
STATUS_COLORS = {
    'open': 'table-warning',
    'In-repair': 'table-info',
    'Repaired': 'table-success',
    'paid': 'table-secondary',
    "can't-repair": 'table-danger'
}

app = create_app()

@app.route('/')
def index():
    return redirect(url_for('view_repairs'))

@app.route('/invoice/new', methods=['GET', 'POST'])
def new_invoice():
    if request.method == 'POST':
        # Create customer first
        customer = Customer(
            name=request.form['name'],
            contact_number=request.form['contact_number'],
            email=request.form.get('email', '')
        )
        db.session.add(customer)
        db.session.commit()

        # Create repair job with minimal info (no laptop fields)
        current_ym = datetime.now().strftime("%y%m")
        counter = JobCounter.query.filter_by(year_month=current_ym).first()
        if not counter:
            counter = JobCounter(year_month=current_ym, last_number=0)
            db.session.add(counter)
        counter.last_number += 1
        job_number = f'JOB{current_ym}{counter.last_number:03d}'

        repair = RepairJob(
            customer_id=customer.id,
            job_number=job_number,
            laptop_model=request.form.get('laptop_model', ''),
            status='Repaired'
        )
        db.session.add(repair)
        db.session.flush()

        # Create invoice
        invoice = RepairInvoice(
            repair_job_id=repair.id,
            total_amount=request.form['total_amount'],
            advance_payment=request.form.get('advance_payment', 0),
            status='pending'
        )
        db.session.add(invoice)
        db.session.flush()

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

        db.session.commit()
        flash('Invoice created successfully!')
        return redirect(url_for('view_invoice', invoice_id=invoice.id))
    
    return render_template('new_invoice.html', today=datetime.now())

@app.route('/repairs')
def view_repairs():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    active_only = request.args.get('active_only')
    
    query = RepairJob.query
    
    if search:
        query = query.join(Customer).filter(
            or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.contact_number.ilike(f'%{search}%'),
                RepairJob.laptop_model.ilike(f'%{search}%'),
                RepairJob.job_number.ilike(f'%{search}%')
            )
        )
    
    if active_only:
        query = query.filter(RepairJob.status.in_(['open', 'In-repair']))
    
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
    unpaid_only = request.args.get('unpaid_only')
    
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
                Customer.contact_number.ilike(f'%{search}%'),
                RepairJob.job_number.ilike(f'%{search}%'),
                amount_condition
            )
        )
    
    if unpaid_only:
        query = query.filter(RepairInvoice.status == 'pending')
    
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
        
        repair = RepairJob(
            customer_id=customer.id,
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
            ssd_status=request.form['ssd_status'],  # Add this line
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
            advance_payment=request.form.get('advance_payment', 0),
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
    repair.ssd_status = request.form['ssd_status']  # Add this line
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
    invoice.advance_payment = request.form.get('advance_payment', 0)
    db.session.commit()
    flash('Invoice updated successfully!')
    return redirect(url_for('view_invoice', invoice_id=invoice_id))

@app.route('/invoice/<int:invoice_id>/mark_paid', methods=['POST'])
def mark_invoice_paid(invoice_id):
    invoice = RepairInvoice.query.get_or_404(invoice_id)

    data = request.get_json(force=True, silent=True) or {}
    payment_method = data.get('payment_method', 'cash')
    if payment_method not in ('cash', 'bank'):
        return jsonify({'success': False, 'message': 'Invalid payment method'}), 400

    try:
        invoice.status = 'paid'
        invoice.repair_job.status = 'paid'
        sale = Sale(
            invoice_id=invoice.id,
            amount=invoice.total_amount,
            payment_method=payment_method
        )
        db.session.add(sale)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Invoice marked as paid successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to mark invoice as paid'}), 500

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
    heading = request.args.get('heading', 'INVOICE').upper()
    if heading not in ('INVOICE', 'QUOTATION'):
        heading = 'INVOICE'
    if not invoice.repair_job.laptop_model:
        return render_template('print_item_invoice.html', invoice=invoice, heading=heading)
    return render_template('print_invoice.html', invoice=invoice, heading=heading)

@app.route('/repair/<int:repair_id>/print')
def print_repair(repair_id):
    repair = RepairJob.query.get_or_404(repair_id)
    return render_template('print_repair.html', repair=repair)

@app.route('/sales')
def view_sales():
    period = request.args.get('period', 'week')  # 'week' or 'month'
    offset = request.args.get('offset', 0, type=int)  # 0 = current, -1 = previous, etc.

    now = datetime.now()
    if period == 'week':
        # Week starts Monday
        start_of_current = now - timedelta(days=now.weekday())
        start_of_current = start_of_current.replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = start_of_current + timedelta(weeks=offset)
        period_end = period_start + timedelta(weeks=1)
        period_label = f"Week of {period_start.strftime('%d %b %Y')}"
    else:
        month = (now.month - 1 + offset) % 12 + 1
        year = now.year + ((now.month - 1 + offset) // 12)
        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1)
        else:
            period_end = datetime(year, month + 1, 1)
        period_label = period_start.strftime('%B %Y')

    sales = Sale.query.filter(Sale.sale_date >= period_start, Sale.sale_date < period_end).order_by(Sale.sale_date.desc()).all()
    manual_entries = ManualEntry.query.filter(ManualEntry.date >= period_start, ManualEntry.date < period_end).order_by(ManualEntry.date.desc()).all()

    money_in = [e for e in manual_entries if e.entry_type == 'in']
    money_out = [e for e in manual_entries if e.entry_type == 'out']
    transfers = [e for e in manual_entries if e.entry_type == 'transfer']

    total_invoice_sales = sum(float(s.amount) for s in sales)
    total_manual_in = sum(float(e.amount) for e in money_in)
    total_sales = total_invoice_sales + total_manual_in

    cash_from_invoices = sum(float(s.amount) for s in sales if s.payment_method == 'cash')
    cash_manual_in = sum(float(e.amount) for e in money_in if e.payment_method == 'cash')
    bank_from_invoices = sum(float(s.amount) for s in sales if s.payment_method == 'bank')
    bank_manual_in = sum(float(e.amount) for e in money_in if e.payment_method == 'bank')

    total_cash_in = cash_from_invoices + cash_manual_in
    total_bank_in = bank_from_invoices + bank_manual_in

    total_out = sum(float(e.amount) for e in money_out)
    total_transfers = sum(float(e.amount) for e in transfers)

    cash_on_hand = total_cash_in - sum(float(e.amount) for e in money_out if e.payment_method == 'cash') - total_transfers
    cash_in_bank = total_bank_in - sum(float(e.amount) for e in money_out if e.payment_method == 'bank') + total_transfers
    net = total_sales - total_out

    return render_template('sales.html',
        sales=sales,
        money_in=money_in,
        money_out=money_out,
        transfers=transfers,
        total_sales=total_sales,
        total_invoice_sales=total_invoice_sales,
        total_manual_in=total_manual_in,
        total_out=total_out,
        total_transfers=total_transfers,
        cash_on_hand=cash_on_hand,
        cash_in_bank=cash_in_bank,
        net=net,
        period=period,
        offset=offset,
        period_label=period_label,
        now=now
    )


@app.route('/sales/entry/add', methods=['POST'])
def add_manual_entry():
    description = request.form.get('description', '').strip()
    amount = request.form.get('amount')
    entry_type = request.form.get('entry_type')
    payment_method = request.form.get('payment_method', 'cash')
    date_str = request.form.get('date')

    if not description or not amount or entry_type not in ('in', 'out', 'transfer'):
        flash('All fields are required.')
        return redirect(url_for('view_sales'))

    entry = ManualEntry(
        description=description,
        amount=amount,
        entry_type=entry_type,
        payment_method=payment_method,
        date=datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()
    )
    db.session.add(entry)
    db.session.commit()
    return redirect(request.referrer or url_for('view_sales'))


@app.route('/sales/entry/<int:entry_id>/delete', methods=['POST'])
def delete_manual_entry(entry_id):
    entry = ManualEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(request.referrer or url_for('view_sales'))


if __name__ == '__main__':
    # Suppress Flask development server warnings
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *args, **kwargs: None
    logging.getLogger('werkzeug').disabled = True
    
    def open_browser():
        """Open browser after a short delay"""
        time.sleep(2)
        try:
            webbrowser.open('http://127.0.0.1:5000')
        except:
            try:
                os.system('start http://127.0.0.1:5000')
            except:
                pass

    # Start browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Flask app
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False
    )