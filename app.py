
from flask import Flask, render_template, redirect, url_for, request, jsonify
import os, json
from datetime import datetime

#------------------Flask App Initialization------------------
app = Flask(__name__, template_folder='template')
Data_File = os.path.join(os.path.dirname(__file__), 'user_data.json')

# Exchange rates (static for now - can be updated from API)
EXCHANGE_RATES = {
    'USD': 1.0,
    'PKR': 278.0,
    'EUR': 0.92
}

#------------------Routing for HTML Pages------------------
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/wallet")
def wallet():
    return render_template("wallet.html")

@app.route("/currency")
def currency():
    return render_template("currency.html")

@app.route("/history")
def history():
    return render_template("history.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/help")
def help():
    return render_template("help.html")

@app.route("/logout")
def logout():
    return redirect(url_for("login"))

#----------------Loading and Saving User Data------------------
def loadalldata():
    if os.path.exists(Data_File):
        try:
            with open(Data_File, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def savealldata(d):
    temp = Data_File + '.temp'
    try:
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2)
        os.replace(temp, Data_File)
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass

#----------------API Endpoints for User Data------------------
@app.route('/api/save', methods=['POST'])
def api_save():
    payload = request.get_json() or {}
    username = payload.get('username')
    data = payload.get('data')
    if not username or data is None:
        return jsonify({'status':'error','message':'username and data required'}), 400
    try:
        all_data = loadalldata()
        all_data[username] = data
        savealldata(all_data)
    except Exception as e:
        return jsonify({'status':'error','message':'save failed'}), 500
    return jsonify({'status':'ok'})

@app.route('/api/load/<username>', methods=['GET'])
def api_load(username):
    all_data = loadalldata()
    user = all_data.get(username, {})
    return jsonify({'status':'ok','data':user})

@app.route('/api/load', methods=['GET'])
def api_load_q():
    username = request.args.get('username')
    if not username:
        return jsonify({'status':'error','message':'username required'}), 400
    return api_load(username)

#----------------API Endpoints for Expenses------------------
@app.route('/api/delete-expense', methods=['POST'])
def delete_expense():
    payload = request.get_json() or {}
    username = payload.get('username')
    expense_index = payload.get('index')
    
    if not username or expense_index is None:
        return jsonify({'status':'error','message':'username and index required'}), 400
    
    try:
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        expenses = all_data[username].get('expenses', [])
        if 0 <= expense_index < len(expenses):
            deleted = expenses.pop(expense_index)
            # Add back the deleted amount to balance
            all_data[username]['balance'] = all_data[username].get('balance', 0) + deleted.get('amount', 0)
            savealldata(all_data)
            return jsonify({'status':'ok','message':'Expense deleted'})
        else:
            return jsonify({'status':'error','message':'invalid index'}), 400
    except Exception as e:
        return jsonify({'status':'error','message':'delete failed'}), 500

@app.route('/api/edit-expense', methods=['POST'])
def edit_expense():
    payload = request.get_json() or {}
    username = payload.get('username')
    expense_index = payload.get('index')
    category = payload.get('category')
    amount = payload.get('amount')
    
    if not username or expense_index is None or not category or amount is None:
        return jsonify({'status':'error','message':'all fields required'}), 400
    
    try:
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        expenses = all_data[username].get('expenses', [])
        if 0 <= expense_index < len(expenses):
            old_amount = expenses[expense_index].get('amount', 0)
            # Update balance: remove old amount, add new amount
            all_data[username]['balance'] = all_data[username].get('balance', 0) + old_amount - amount
            # Update expense
            expenses[expense_index]['category'] = category
            expenses[expense_index]['amount'] = amount
            savealldata(all_data)
            return jsonify({'status':'ok','message':'Expense updated'})
        else:
            return jsonify({'status':'error','message':'invalid index'}), 400
    except Exception as e:
        return jsonify({'status':'error','message':'edit failed'}), 500

#----------------API Endpoint for Currency Conversion------------------
@app.route('/api/convert-currency', methods=['POST'])
def convert_currency():
    payload = request.get_json() or {}
    username = payload.get('username')
    new_currency = payload.get('currency')
    
    if not username or not new_currency:
        return jsonify({'status':'error','message':'username and currency required'}), 400
    
    if new_currency not in EXCHANGE_RATES:
        return jsonify({'status':'error','message':'invalid currency'}), 400
    
    try:
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        user_data = all_data[username]
        old_currency = user_data.get('currency', 'USD')
        
        # Convert balance from old currency to USD, then to new currency
        if old_currency != new_currency and old_currency in EXCHANGE_RATES:
            # Convert to USD first
            balance_usd = user_data.get('balance', 0) / EXCHANGE_RATES[old_currency]
            # Convert to new currency
            new_balance = balance_usd * EXCHANGE_RATES[new_currency]
            user_data['balance'] = round(new_balance, 2)
            
            # Also convert all expenses
            for expense in user_data.get('expenses', []):
                expense_usd = expense.get('amount', 0) / EXCHANGE_RATES[old_currency]
                expense['amount'] = round(expense_usd * EXCHANGE_RATES[new_currency], 2)
            
            # Convert savings
            if 'savings' in user_data:
                savings_usd = user_data['savings'] / EXCHANGE_RATES[old_currency]
                user_data['savings'] = round(savings_usd * EXCHANGE_RATES[new_currency], 2)
        
        user_data['currency'] = new_currency
        savealldata(all_data)
        return jsonify({'status':'ok','data':user_data})
    except Exception as e:
        return jsonify({'status':'error','message':'conversion failed'}), 500

#----------------API Endpoints for Wallet Management------------------
@app.route('/api/edit-balance', methods=['POST'])
def edit_balance():
    payload = request.get_json() or {}
    username = payload.get('username')
    new_balance = payload.get('balance')
    
    if not username or new_balance is None:
        return jsonify({'status':'error','message':'username and balance required'}), 400
    
    try:
        new_balance = float(new_balance)
        if new_balance < 0:
            return jsonify({'status':'error','message':'balance cannot be negative'}), 400
        
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        all_data[username]['balance'] = round(new_balance, 2)
        savealldata(all_data)
        return jsonify({'status':'ok','data':all_data[username]})
    except Exception as e:
        return jsonify({'status':'error','message':'edit balance failed'}), 500

@app.route('/api/delete-balance', methods=['POST'])
def delete_balance():
    payload = request.get_json() or {}
    username = payload.get('username')
    
    if not username:
        return jsonify({'status':'error','message':'username required'}), 400
    
    try:
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        all_data[username]['balance'] = 0
        savealldata(all_data)
        return jsonify({'status':'ok','data':all_data[username]})
    except Exception as e:
        return jsonify({'status':'error','message':'delete balance failed'}), 500

@app.route('/api/edit-savings', methods=['POST'])
def edit_savings():
    payload = request.get_json() or {}
    username = payload.get('username')
    new_savings = payload.get('savings')
    
    if not username or new_savings is None:
        return jsonify({'status':'error','message':'username and savings required'}), 400
    
    try:
        new_savings = float(new_savings)
        if new_savings < 0:
            return jsonify({'status':'error','message':'savings cannot be negative'}), 400
        
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        all_data[username]['savings'] = round(new_savings, 2)
        savealldata(all_data)
        return jsonify({'status':'ok','data':all_data[username]})
    except Exception as e:
        return jsonify({'status':'error','message':'edit savings failed'}), 500

@app.route('/api/delete-savings', methods=['POST'])
def delete_savings():
    payload = request.get_json() or {}
    username = payload.get('username')
    
    if not username:
        return jsonify({'status':'error','message':'username required'}), 400
    
    try:
        all_data = loadalldata()
        if username not in all_data:
            return jsonify({'status':'error','message':'user not found'}), 404
        
        all_data[username]['savings'] = 0
        savealldata(all_data)
        return jsonify({'status':'ok','data':all_data[username]})
    except Exception as e:
        return jsonify({'status':'error','message':'delete savings failed'}), 500

if __name__ == "__main__":
    app.run(debug=True)

