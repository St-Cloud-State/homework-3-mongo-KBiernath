# app.py
import os
from flask import Flask, request, render_template
import pymongo
from pymongo import ReturnDocument

app = Flask(__name__)

client       = pymongo.MongoClient("mongodb://localhost:27017/")
db           = client['acme_financial']
applications = db['applications']
counters     = db['counters']

def get_next_sequence(name):
    counter = counters.find_one_and_update(
        {'_id': name},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return counter['seq']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/accept_application', methods=['POST'])
def accept_application():
    name    = request.form.get('name', '').strip()
    zipcode = request.form.get('zipcode', '').strip()
    if not name or not zipcode:
        return render_template('index.html',
                               accept_msg="Error: Name and ZIP code are required.")

    app_num = get_next_sequence('application_number')
    applications.insert_one({
        'app_number': app_num,
        'name': name,
        'zipcode': zipcode,
        'status': 'received',
        'notes': []
    })

    msg = f"Application accepted. Your application number is <strong>{app_num}</strong>."
    return render_template('index.html', accept_msg=msg)


@app.route('/check_status', methods=['POST'])
def check_status():
    app_id = request.form.get('application_number', '').strip()
    if not app_id:
        return render_template('index.html',
                               check_msg="Error: Application number is required.")
    try:
        app_num = int(app_id)
    except ValueError:
        return render_template('index.html',
                               check_msg="Error: Application number must be numeric.")

    doc = applications.find_one({'app_number': app_num})
    if not doc:
        return render_template('index.html',
                               check_msg=f"Application #{app_id} not found.")

    status     = doc.get('status', 'unknown')
    notes      = doc.get('notes', [])
    notes_html = '<br>'.join(notes) if notes else 'No notes recorded.'

    msg = (
        f"Application #{app_id} status: <strong>{status}</strong>.<br>"
        f"<u>Notes:</u><br>{notes_html}"
    )
    return render_template('index.html', check_msg=msg)


@app.route('/change_status', methods=['POST'])
def change_status():
    app_id     = request.form.get('application_number', '').strip()
    new_status = request.form.get('new_status', '').strip()
    note       = request.form.get('note', '').strip()

    if not app_id:
        return render_template('index.html',
                               change_msg="Error: Application number is required.")

    try:
        app_num = int(app_id)
    except ValueError:
        return render_template('index.html',
                               change_msg="Error: Application number must be numeric.")

    doc = applications.find_one({'app_number': app_num})
    if not doc:
        return render_template('index.html',
                               change_msg=f"Application #{app_id} not found.")

    # Build update spec
    update_spec = {}
    if new_status:
        update_spec['$set'] = {'status': new_status}
    if note:
        update_spec.setdefault('$push', {})['notes'] = note

    if not update_spec:
        return render_template('index.html',
                               change_msg="Error: Please select a new status or enter a note.")

    # Perform update
    applications.update_one({'app_number': app_num}, update_spec)

    # Build user message
    parts = []
    if new_status:
        parts.append(f"Status changed to '<strong>{new_status}</strong>'.")
    if note:
        parts.append(f"Note added: \"{note}\"")

    msg = " ".join(parts)
    return render_template('index.html', change_msg=msg)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
