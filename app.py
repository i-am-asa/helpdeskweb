from flask import Flask, render_template, request, redirect, flash, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import psycopg2
from datetime import datetime
from flask_mail import Mail, Message
from flask import jsonify
from datetime import datetime
from flask import session


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a secure secret key

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'helpdeskteamofficial@gmail.com'
app.config['MAIL_PASSWORD'] = 'tiup xdae jvnu hlex'

# Initialize Flask-Mail
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)

conn = psycopg2.connect(
    dbname='onlinehelpdesk',
    user='postgres',
    password='admindata',
    host='database-2.cpqq4g4i2zk6.us-east-2.rds.amazonaws.com',
    port='5432'
)

class User:
    def __init__(self, user_id, username, full_name, email):
        self.id = user_id
        self.username = username
        self.full_name = full_name
        self.email = email

    def get_id(self):
        return str(self.id)

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

@login_manager.user_loader
def load_user(user_id):
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, full_name, email FROM users_table WHERE user_id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        user_id, username, full_name, email = user_data
        return User(user_id, username, full_name, email)
    return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database for the user
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, password, full_name, email FROM users_table WHERE username = %s", (username,))
        user_data = cur.fetchone()
        cur.close()

        if user_data:
            user_id, db_username, db_password, full_name, email = user_data
            # Check if the password matches
            if password == db_password:
                user = User(user_id, db_username, full_name, email)
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password", "danger")
        else:
            flash("User not found", "danger")

    return render_template('login.html')

from flask import redirect, url_for

from flask import session

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database for the user
        cur = conn.cursor()
        cur.execute("SELECT password, is_admin, department FROM admin WHERE username = %s", (username,))
        user_data = cur.fetchone()
        cur.close()

        if user_data:
            db_password, is_admin, department = user_data
            # Check if the provided password is correct
            if password == db_password:
                if is_admin == 1:
                    # Log in the admin user
                    user = User(user_id=0, username='admin', full_name='Admin', email='admin@example.com')
                    login_user(user)
                    return redirect(url_for('admin_dashboard'))
                else:
                    # Set the department information in the session and redirect to the department dashboard
                    session['department'] = department
                    return redirect(url_for('department_dashboard'))
            else:
                flash("Incorrect password", "danger")
        else:
            flash("User not found", "danger")

    return render_template('admin_login.html')




@app.route('/admin_dashboard')
#@login_required
def admin_dashboard():
    cur = conn.cursor()
    cur.execute("""
        SELECT t.ticket_id, u.full_name, t.title, t.description, t.priority, 
               t.status, t.raised_time, t.department, t.assigned_time, t.resolve_time
        FROM tickets t
        JOIN users_table u ON t.user_id = u.user_id
    """)
    tickets = cur.fetchall()
    cur.close()
    return render_template('admin_dashboard.html', tickets=tickets)

@app.route('/delete_ticket/<int:ticket_id>', methods=['POST'])
def delete_ticket(ticket_id):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
        conn.commit()
        cur.close()
        #flash("Ticket deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting ticket: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

from flask_mail import Message

from flask_mail import Message

@app.route('/change_status/<int:ticket_id>', methods=['POST'])
def change_status(ticket_id):
    if request.method == 'POST':
        new_status = request.form['status']
        try:
            cur = conn.cursor()
            cur.execute("UPDATE tickets SET status = %s WHERE ticket_id = %s", (new_status, ticket_id))

            # Update assigned_time or resolve_time based on the new status
            if new_status == 'Assigned':
                cur.execute("UPDATE tickets SET assigned_time = %s WHERE ticket_id = %s", (datetime.now(), ticket_id))
                # Fetch user's email to send the notification
                cur.execute("SELECT email FROM users_table WHERE user_id = (SELECT user_id FROM tickets WHERE ticket_id = %s)", (ticket_id,))
                user_email = cur.fetchone()[0]

                # Send email notification
                send_assigned_email(user_email, ticket_id)
            elif new_status == 'Resolved':
                cur.execute("UPDATE tickets SET resolve_time = %s WHERE ticket_id = %s", (datetime.now(), ticket_id))

                # Fetch user's email to send the notification
                cur.execute("SELECT email FROM users_table WHERE user_id = (SELECT user_id FROM tickets WHERE ticket_id = %s)", (ticket_id,))
                user_email = cur.fetchone()[0]

                # Send email notification
                send_resolution_email(user_email, ticket_id)

            conn.commit()
            cur.close()
            #flash("Status updated successfully", "success")
        except Exception as e:
            flash(f"Error updating status: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

def send_assigned_email(user_email, ticket_id):
    msg = Message('Ticket Assigned Update', sender='helpdeskteamofficial@gmail.com', recipients=[user_email])
    msg.body = f"Hello,\n\nYour ticket with ID {ticket_id} has been assigned to an agent. Please log in to the website for further details."
    
    try:
        mail.send(msg)
        print("Email sent successfully to " + user_email)
    except Exception as e:
        print("Error sending email:", e)


def send_resolution_email(user_email, ticket_id):
    msg = Message('Ticket Resolution Update', sender='helpdeskteamofficial@gmail.com', recipients=[user_email])
    msg.body = f"Hello,\n\nYour ticket with ID {ticket_id} has been resolved. Please log in to the website to review and accept the resolution if satisfactory."
    
    try:
        mail.send(msg)
        print("Email sent successfully to " + user_email)
    except Exception as e:
        print("Error sending email:", e)


@app.route('/change_status_department/<int:ticket_id>', methods=['POST'])
def change_status_department(ticket_id):
    if request.method == 'POST':
        new_status = request.form['status']
        try:
            cur = conn.cursor()
            cur.execute("UPDATE tickets SET status = %s WHERE ticket_id = %s", (new_status, ticket_id))

            # Update assigned_time or resolve_time based on the new status
            if new_status == 'Assigned':
                cur.execute("UPDATE tickets SET assigned_time = %s WHERE ticket_id = %s", (datetime.now(), ticket_id))
                # Fetch user's email to send the notification
                cur.execute("SELECT email FROM users_table WHERE user_id = (SELECT user_id FROM tickets WHERE ticket_id = %s)", (ticket_id,))
                user_email = cur.fetchone()[0]

                # Send email notification
                send_assigned_email(user_email, ticket_id)
            elif new_status == 'Resolved':
                cur.execute("UPDATE tickets SET resolve_time = %s WHERE ticket_id = %s", (datetime.now(), ticket_id))

                # Fetch user's email to send the notification
                cur.execute("SELECT email FROM users_table WHERE user_id = (SELECT user_id FROM tickets WHERE ticket_id = %s)", (ticket_id,))
                user_email = cur.fetchone()[0]

                # Send email notification
                send_resolution_email(user_email, ticket_id)

            conn.commit()
            cur.close()
            #flash("Status updated successfully", "success")
        except Exception as e:
            flash(f"Error updating status: {str(e)}", "danger")
    return redirect(url_for('department_dashboard'))



@app.route('/tickets_by_department')
def tickets_by_department():
    department = request.args.get('department')

    if department == 'all':
        # Fetch all tickets
        cur = conn.cursor()
        cur.execute("""
            SELECT t.ticket_id, u.full_name, t.title, t.description, t.priority, 
                   t.status, t.raised_time, t.department, t.assigned_time, t.resolve_time
            FROM tickets t
            JOIN users_table u ON t.user_id = u.user_id
        """)
        tickets = cur.fetchall()
        cur.close()
    else:
        # Fetch tickets for the selected department
        cur = conn.cursor()
        cur.execute("""
            SELECT t.ticket_id, u.full_name, t.title, t.description, t.priority, 
                   t.status, t.raised_time, t.department, t.assigned_time, t.resolve_time
            FROM tickets t
            JOIN users_table u ON t.user_id = u.user_id
            WHERE t.department = %s
        """, (department,))
        tickets = cur.fetchall()
        cur.close()

    # Convert the fetched data into a list of dictionaries
    tickets_data = []
    for ticket in tickets:
        ticket_dict = {
            "ticket_id": ticket[0],
            "full_name": ticket[1],
            "title": ticket[2],
            "description": ticket[3],
            "priority": ticket[4],
            "status": ticket[5],
            "raised_time": ticket[6],
            "department": ticket[7],
            "assigned_time": ticket[8],
            "resolve_time": ticket[9]
        }
        tickets_data.append(ticket_dict)

    # Return the tickets data as JSON response
    return jsonify(tickets=tickets_data)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', full_name=current_user.full_name)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/logout_dept')
def logout_dept():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form['email']

        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users_table (username, password, full_name, email) VALUES (%s, %s, %s, %s)",
                        (username, password, full_name, email))
            conn.commit()
            send_signup_email(username, email,password)
            flash("Signup successful! User can now login.", "success")
            cur.close()
            return redirect(url_for('login'))
        except psycopg2.IntegrityError as e:
            conn.rollback()
            cur.close()
            flash("Username or email already exists.", "danger")

    return render_template('signup.html')

from flask_mail import Message

def send_signup_email(username, email, password):
    msg = Message('Welcome to Our Platform!', sender='helpdeskteamofficial@gmail.com', recipients=[email])
    msg.body = f"Hello {username},\n\nThank you for signing up! Here are your credentials:\n\nUsername: {username}\nPassword: {password}\n\nYou can now login to your account."
    
    try:
        mail.send(msg)
        print("Email sent successfully to " + email)
    except Exception as e:
        print("Error sending email:", e)



# Route for FAQ page
@app.route('/faqs')
@login_required
def faqs():
    return render_template('faq.html')

# Route for displaying the raise ticket form
@app.route('/raise_ticket')
@login_required
# Modify the raise_ticket function to fetch both issue_type and code
def raise_ticket():
    cur = conn.cursor()
    # Query the database for issue types
    cur.execute("SELECT issue_type FROM issue")
    issues = cur.fetchall()
    cur.close()
    return render_template('raise_ticket.html', issues=issues)


@app.route('/submit_ticket', methods=['POST'])
@login_required
def submit_ticket():
    # Get form data from request
    issue_type = request.form.get('issue_type')
    description = request.form.get('description')
    severity = int(request.form.get('severity'))
    
    # Get the current user's ID
    user_id = current_user.id

    # Connect to the database
    cur = conn.cursor()

    # Fetch priority and department based on the selected issue type from the 'issue' table
    cur.execute("SELECT priority, department FROM issue WHERE issue_type = %s", (issue_type,))
    issue_details = cur.fetchone()
    if issue_details:
        priority, department = issue_details

        # Insert the ticket into the 'tickets' table with status as 'Pending'
        cur.execute(
            """
            INSERT INTO tickets (user_id, title, description, priority, status, raised_time, department, severity)
            VALUES (%s, %s, %s, %s, 'Pending', %s, %s, %s)
            """,
            (user_id, issue_type, description, priority, datetime.now(), department, severity)
        )
        # Commit the transaction to the database
        conn.commit()
        
        # Close the cursor
        cur.close()

        # Flash a success message
        #flash('Ticket raised successfully!', 'success')
        return redirect(url_for('dashboard'))  # Redirect to home (dashboard) page
    else:
        # Close the cursor
        cur.close()
        
        # Flash an error message if issue details were not found
        flash('Invalid issue type selected.', 'error')
        return redirect(url_for('raise_ticket'))



# Route for viewing previous tickets
@app.route('/view_tickets')
@login_required
def view_tickets():
    # Functionality to display previous tickets
    cur = conn.cursor()
    cur.execute("SELECT * FROM tickets WHERE user_id = %s", (current_user.id,))
    tickets = cur.fetchall()
    cur.close()
    return render_template('view_tickets.html', tickets=tickets)

from flask import request

@app.route('/resolve_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def resolve_ticket(ticket_id):
    if request.method == 'POST':
        decision = request.form['decision']
        
        # Logic to handle the user's decision
        if decision == 'accept':
            # Close the ticket
            try:
                cur = conn.cursor()
                cur.execute("UPDATE tickets SET status = 'Closed' WHERE ticket_id = %s", (ticket_id,))
                conn.commit()
                cur.close()
                #flash("Resolution accepted. Ticket closed successfully.", "success")
            except Exception as e:
                flash(f"Error closing ticket: {str(e)}", "danger")
        elif decision == 'reject':
            # Reopen the ticket
            try:
                cur = conn.cursor()
                cur.execute("UPDATE tickets SET status = 'Open' WHERE ticket_id = %s", (ticket_id,))
                conn.commit()
                cur.close()
                
            except Exception as e:
                flash(f"Error reopening ticket: {str(e)}", "danger")

    return redirect(url_for('view_tickets'))


@app.route('/department_dashboard')
#@login_required
def department_dashboard():
    department = session.get('department')  # Assuming you store the department in the session after login

    if not department:
        
        return redirect(url_for('index'))  # Redirect to the login page or homepage

    cur = conn.cursor()
    cur.execute("""
        SELECT t.ticket_id, u.full_name, t.title, t.description, t.priority, 
               t.status, t.raised_time, t.assigned_time, t.resolve_time
        FROM tickets t
        JOIN users_table u ON t.user_id = u.user_id
        WHERE t.department = %s
    """, (department,))
    tickets = cur.fetchall()
    cur.close()

    return render_template('department_dashboard.html', department=department, tickets=tickets)



if __name__ == '__main__':
    app.run(debug=True)
