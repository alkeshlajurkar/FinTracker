from flask import Flask, request, redirect, url_for, render_template, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong secret key

# Database connection
def create_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="manager",
            database="personalfinancetracker_db"
        )
    except mysql.connector.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Initialize DB
def init_db():
    db = create_connection()
    if db:
        try:
            cursor = db.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                password VARCHAR(255))''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                category VARCHAR(255),
                amount FLOAT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS income (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                amount FLOAT NOT NULL,
                source VARCHAR(255) NOT NULL,
                description TEXT DEFAULT NULL,
                category VARCHAR(255) DEFAULT NULL,
                transaction_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
            db.commit()
        except mysql.connector.Error as e:
            print(f"Error initializing database: {e}")
        finally:
            cursor.close()
            db.close()

@app.route('/')
def home():
    return render_template('login.html')

# Route for viewing income transactions
@app.route('/income')
def income():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    db = create_connection()
    expenses = []

    if db is not None:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, amount, source, description, category, transaction_date, created_at,updated_at FROM income WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,))
        income = cursor.fetchall()
        cursor.close()
        db.close()

    return render_template('income.html', income=income)

# Route to add income transaction
@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        user_id = session.get('user_id')
        amount = request.form.get('amount')
        source = request.form.get('source')
        description = request.form.get('description')
        category = request.form.get('category')
        transaction_date = request.form.get('transaction_date')

        db = create_connection()

        if db is not None:
            cursor = db.cursor()
            cursor.execute("""
                    INSERT INTO income (user_id, amount, source, description, category, transaction_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, amount, source, description, category, transaction_date))
            db.commit()
            flash("Income added successfully!")
            return redirect(url_for('dashboard'))

    return render_template('add_income.html')

# Route to edit income transaction
@app.route('/edit_income/<int:income_id>', methods=['GET', 'POST'])
def edit_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))

    db = create_connection()
    income = None

    if db is not None:
        cursor = db.cursor()
        cursor.execute("SELECT id, amount, source, description, category, transaction_date FROM income WHERE id = %s", (income_id,))
        income = cursor.fetchone()  # Fetch the income record
        cursor.close()
        db.close()

    if not income:
        flash("Income record not found!")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            user_id = session['user_id']
            amount = request.form['amount']
            source = request.form['source']
            description = request.form['description']
            category = request.form['category']
            transaction_date = request.form['transaction_date']

            db = create_connection()
            if db is not None:
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE income
                    SET amount=%s, source=%s, description=%s, category=%s, transaction_date=%s
                    WHERE id=%s AND user_id=%s
                """, (amount, source, description, category, transaction_date, income_id, user_id))
                db.commit()
                flash("Income updated successfully!")
                cursor.close()
                db.close()
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('edit_income', income_id=income_id))

    # Prepare date in the correct format for the template
    income_date = income[5].strftime('%Y-%m-%d') if income[5] else ''

    return render_template('edit_income.html', ic=income, income_date=income_date)


# Route to delete income transaction
@app.route('/delete_income/<int:income_id>', methods=['POST'])
def delete_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))

    db = create_connection()

    if db is not None:
        cursor = db.cursor()
        cursor.execute("DELETE FROM income WHERE id = %s", (income_id,))
        db.commit()
        flash("Income deleted successfully!")
        cursor.close()
        db.close()

    return redirect(url_for('dashboard'))

@app.route('/expense')
def expense():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    db = create_connection()
    expenses = []

    if db is not None:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, category, amount, created_at, updated_at, comment FROM expenses WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,))
        expenses = cursor.fetchall()
        cursor.close()
        db.close()

    return render_template('expense.html', expenses=expenses)

# Route to add expense transaction
@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        comment = request.form['comment']
        user_id = session['user_id']
        db = create_connection()

        if db is not None:
            cursor = db.cursor()
            cursor.execute("INSERT INTO expenses (user_id, category, amount, comment) VALUES (%s, %s, %s, %s)",
                           (user_id, category, amount, comment))
            db.commit()
            flash("Expense added successfully!")
            return redirect(url_for('dashboard'))

    return render_template('add_expense.html')

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))

    db = create_connection()
    expense = None

    if db is not None:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
        expense = cursor.fetchone()
        cursor.close()
        db.close()

    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        comment = request.form['comment']
        user_id = session['user_id']

        db = create_connection()
        if db is not None:
            cursor = db.cursor()
            cursor.execute("UPDATE expenses SET category = %s, amount = %s, comment = %s WHERE id = %s",
                           (category, amount, comment, expense_id))
            db.commit()
            flash("Expense updated successfully!")
            cursor.close()
            db.close()
            return redirect(url_for('dashboard'))

    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))

    db = create_connection()

    if db is not None:
        cursor = db.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        db.commit()
        flash("Expense deleted successfully!")
        cursor.close()
        db.close()

    return redirect(url_for('dashboard'))

@app.route('/transactions')
def transactions():
    return "transactions Page"


import matplotlib.pyplot as plt
import io
import base64
from flask import render_template, redirect, url_for, session
import mysql.connector

@app.route('/statistics', methods=['GET'])
def statistics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = create_connection()
    total_income = 0
    total_expense = 0
    category_expenses = {}  
    income_sources = {}    

    if db is not None:
        cursor = db.cursor()

        # Fetch total income
        cursor.execute("SELECT SUM(amount) FROM income WHERE user_id = %s", (session['user_id'],))
        total_income = cursor.fetchone()[0] or 0

        # Fetch total expense
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = %s", (session['user_id'],))
        total_expense = cursor.fetchone()[0] or 0

        # Fetch expense breakdown by category
        cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = %s GROUP BY category", (session['user_id'],))
        for row in cursor.fetchall():
            category_expenses[row[0]] = row[1]

        # Fetch income breakdown by source
        cursor.execute("SELECT source, SUM(amount) FROM income WHERE user_id = %s GROUP BY source", (session['user_id'],))
        for row in cursor.fetchall():
            income_sources[row[0]] = row[1]

        cursor.close()
        db.close()

    # Create charts

    # Bar chart for Income vs Expense
    labels = ['Income', 'Expense']
    amounts = [total_income, total_expense]
    plt.figure(figsize=(5, 3))
    plt.bar(labels, amounts, color=['green', 'red'])
    plt.title('Income vs Expense')
    plt.xlabel('Category')
    plt.ylabel('Amount')
    img1 = io.BytesIO()
    plt.savefig(img1, format='png')
    img1.seek(0)
    plot_url1 = base64.b64encode(img1.getvalue()).decode('utf8')
    plt.close()

    # Pie chart for Expense Distribution by Category
    categories = list(category_expenses.keys())
    expenses = list(category_expenses.values())
    plt.figure(figsize=(5, 5))
    plt.pie(expenses, labels=categories, autopct='%1.1f%%', startangle=140)
    plt.title('Expense Distribution by Category')
    img2 = io.BytesIO()
    plt.savefig(img2, format='png')
    img2.seek(0)
    plot_url2 = base64.b64encode(img2.getvalue()).decode('utf8')
    plt.close()

    # Pie chart for Income Distribution by Source
    sources = list(income_sources.keys())
    incomes = list(income_sources.values())
    plt.figure(figsize=(5, 5))
    plt.pie(incomes, labels=sources, autopct='%1.1f%%', startangle=140)
    plt.title('Income Distribution by Source')
    img3 = io.BytesIO()
    plt.savefig(img3, format='png')
    img3.seek(0)
    plot_url3 = base64.b64encode(img3.getvalue()).decode('utf8')
    plt.close()

    return render_template('statistics.html', plot_url1=plot_url1, plot_url2=plot_url2, plot_url3=plot_url3)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = create_connection()

        if db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash("User already exists. Please choose a different username.", "danger")
                return redirect(url_for('signup'))

            hashed_password = generate_password_hash(password)
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
                db.commit()
                flash("Registration successful! You can now log in.", "success")
                return redirect(url_for('home'))
            except mysql.connector.Error as e:
                flash(f"Error during registration: {e}", "danger")
                return redirect(url_for('signup'))
            finally:
                cursor.close()
                db.close()

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = create_connection()

        if db:
            cursor = db.cursor()
            try:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()

                if user and check_password_hash(user[2], password):  # user[2] is the hashed password
                    session['user_id'] = user[0]  # Store user ID in session
                    flash("Login successful!", "success")
                    return redirect(url_for('dashboard'))  # Redirect to dashboard after successful login
                else:
                    flash("Invalid username or password.", "danger")
                    return redirect(url_for('login'))  # Stay on login page if invalid credentials
            except mysql.connector.Error as e:
                flash(f"Error during login: {e}", "danger")
                return redirect(url_for('login'))
            finally:
                cursor.close()  # Ensure cursor is closed
                db.close()  # Close the database connection

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:  # Ensure user is logged in
        return redirect(url_for('home'))
    
    user_id = session['user_id']  # Get logged-in user's ID
    db = create_connection()
    
    income = 0.0
    expenses = 0.0
    available_balance = 0.0

    if db:
        cursor = db.cursor()
        
        # Fetch total income for the user
        cursor.execute("SELECT SUM(amount) FROM income WHERE user_id = %s", (user_id,))
        income_result = cursor.fetchone()
        if income_result and income_result[0]:
            income = income_result[0]
        
        # Fetch total expenses for the user
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = %s", (user_id,))
        expense_result = cursor.fetchone()
        if expense_result and expense_result[0]:
            expenses = expense_result[0]
        
        # Calculate available balance
        available_balance = income - expenses
        
        cursor.close()
        db.close()

    # Pass the calculated values to the template
    return render_template(
        'dashboard.html',
        income=income,
        expenses=expenses,
        available_balance=available_balance
    )
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()  
    app.run(debug=True)
