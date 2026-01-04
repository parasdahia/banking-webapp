import time
import random
from functools import wraps
from datetime import timedelta
from packages.database_manager import DatabaseManager
from flask import Flask, redirect, url_for, render_template, request, session, jsonify


app = Flask(__name__)
app.secret_key = "RANDOM_SECRET_KEY"
app.permanent_session_lifetime = timedelta(minutes=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = False


# Initialize the Manager
db_manager = DatabaseManager()


# LOGIN DECORATOR
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'account_number' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET"])
def login():
    if 'account_number' in session:
        return redirect(url_for('dashboard'))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def validate_user_login():
    time.sleep(random.uniform(0.5, 2.5))  # Simulating
    data = request.json
    identity = data.get('identity')
    password = data.get('password')

    user = db_manager.validate_user(identity, password)

    if user:
        session.permanent = True
        session['account_number'] = user['account_number']
        return jsonify({"message": "Success", "redirect": "/dashboard"})
    else:
        return jsonify({"error": "Invalid Credentials"}), 401


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/get_account_information", methods=["GET"])
@login_required
def get_account_information():
    current_acc_num = session['account_number']
    info = db_manager.get_account_details(current_acc_num)

    if info:
        return jsonify(info)
    else:
        return jsonify({"error": "Unable to fetch account details"}), 500


@app.route("/api/lookup_beneficiary", methods=["POST"])
@login_required
def lookup_beneficiary():
    data = request.json
    mode = data.get('mode')  # 'IMPS' or 'UPI'
    value = data.get('value')

    # User cannot transfer to self
    current_acc_num = session['account_number']

    if mode == 'IMPS':
        # Check if sending to self
        if str(value) == str(current_acc_num):
            return jsonify({"valid": False, "error": "Cannot transfer to self"})

        info = db_manager.lookup_beneficiary('ACCOUNT', value)
        if info:
            return jsonify({"valid": True, "branch": info['bank_branch'], "name": info['account_holder_name']})

    elif mode == 'UPI':
        info = db_manager.lookup_beneficiary('UPI', value)
        if info:
            # Check if sending to self
            if str(info['account_number']) == str(current_acc_num):
                return jsonify({"valid": False, "error": "Cannot transfer to self"})

            return jsonify({"valid": True, "name": info['account_holder_name']})

    return jsonify({"valid": False, "error": "Invalid Details"})


@app.route("/api/transferFunds", methods=["POST"])
@login_required
def transfer_funds():
    data = request.json
    mode = data.get('mode')
    identifier = data.get('identifier')
    amount = float(data.get('amount'))
    note = data.get('note')

    current_acc_num = session['account_number']

    # Resolve Receiver Account Number
    receiver_acc_num = None

    if mode == 'IMPS':
        receiver_acc_num = identifier
    else:
        info = db_manager.lookup_beneficiary('UPI', identifier)
        if info:
            receiver_acc_num = info['account_number']

    if not receiver_acc_num:
        return jsonify({"error": "Invalid Beneficiary"}), 400

    # Perform Transfer (Now passing mode and note)
    if db_manager.perform_transfer(current_acc_num, receiver_acc_num, amount, mode, note):
        return jsonify({"message": "Transfer Successful!"})
    else:
        return jsonify({"error": "Transfer Failed (Check Balance)"}), 500


@app.route("/api/resetPassword", methods=["POST"])
@login_required
def reset_password():
    data = request.json
    new_password = data.get('new_password')
    current_acc_num = session['account_number']

    if db_manager.update_password(current_acc_num, new_password):
        return jsonify({"message": "Password updated successfully!"})
    else:
        return jsonify({"error": "Failed to update password"}), 500


@app.route("/api/transactions", methods=["GET"])
@login_required
def get_transactions():
    acc_num = session['account_number']
    transactions = db_manager.get_transaction_history(acc_num)

    # Format the data for the frontend
    formatted_data = []
    for t in transactions:
        # Determine if Credit or Debit
        if str(t['sender_account_number']) == str(acc_num):
            trans_type = 'DEBIT'
        else:
            trans_type = 'CREDIT'

        formatted_data.append({
            "id": t['transaction_id'],
            "date": t['transaction_date'].strftime("%d-%b-%Y %I:%M:%S %p"),
            "from": t['sender_name'],
            "to": t['receiver_name'],
            "mode": t['mode'],
            "type": trans_type,
            "amount": float(t['amount']),
            "note": t['note']
        })

    return jsonify(formatted_data)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


# CACHE BUSTING
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == '__main__':
    app.run(debug=False)
