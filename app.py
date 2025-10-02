from flask import Flask, request, redirect, url_for, render_template_string, flash
import mysql.connector
import secrets
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash
import re
import os
import signal
import sys
import time
import socket

app = Flask(__name__)
app.secret_key = 'devsecret'  # direct secret key

# ---------------- Database Config ----------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',        
    'password': '',        
    'database': 'userdb'   
}

# ---------------- SMTP Config ----------------
SMTP_USER = "SMTP_USER"        # Gmail
SMTP_PASS = "SMTP_PASS"         # Gmail App Password
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
FROM_EMAIL = SMTP_USER

# ---------------- Helper Functions for Port Management ----------------
def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_free_port():
    """Find a free port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

# ---------------- Database Functions ----------------
def get_conn():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        flash('Database connection error. Please try again later.', 'error')
        return None

def save_user(email, password_hash, user_id):
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (id,email,password_hash) VALUES (%s,%s,%s)", (user_id,email,password_hash))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error saving user: {err}")
        return False
    finally:
        cur.close()
        conn.close()

def update_password(email, new_hash):
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash=%s WHERE email=%s", (new_hash,email))
        conn.commit()
        updated = cur.rowcount > 0
        return updated
    except mysql.connector.Error as err:
        print(f"Error updating password: {err}")
        return False
    finally:
        cur.close()
        conn.close()

def user_exists(email):
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        return row[0] if row else None
    except mysql.connector.Error as err:
        print(f"Error checking user existence: {err}")
        return None
    finally:
        cur.close()
        conn.close()

# ---------------- Helper Functions ----------------
def generate_credentials():
    user_id = secrets.token_hex(4)        # 8-char ID
    password = secrets.token_urlsafe(8)   # Random password
    return user_id, password

def send_email(to_email, subject, body, is_html=False):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        if is_html:
            msg.add_alternative(body, subtype='html')
        else:
            msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ---------------- Frontend (Modern UI with Tab Switching) ----------------
INDEX_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>User Auth System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
      :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --success-color: #10b981;
        --danger-color: #ef4444;
        --warning-color: #f59e0b;
        --dark-color: #1f2937;
        --light-color: #f9fafb;
      }
      
      body {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      }
      
      .auth-container {
        width: 100%;
        max-width: 450px;
      }
      
      .auth-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        overflow: hidden;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
      }
      
      .auth-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
      }
      
      .auth-header {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        padding: 30px 20px;
        text-align: center;
      }
      
      .auth-header h1 {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 10px;
      }
      
      .auth-header p {
        margin: 0;
        opacity: 0.9;
      }
      
      .auth-tabs {
        display: flex;
        background: rgba(255, 255, 255, 0.7);
        border-bottom: 1px solid rgba(0, 0, 0, 0.1);
      }
      
      .auth-tab {
        flex: 1;
        padding: 15px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 600;
        color: var(--dark-color);
        border: none;
        background: transparent;
      }
      
      .auth-tab.active {
        background: white;
        color: var(--primary-color);
        border-bottom: 3px solid var(--primary-color);
      }
      
      .auth-tab:hover:not(.active) {
        background: rgba(255, 255, 255, 0.5);
      }
      
      .auth-body {
        padding: 30px;
      }
      
      .form-control {
        border-radius: 10px;
        padding: 12px 15px;
        border: 1px solid #e5e7eb;
        transition: all 0.3s ease;
      }
      
      .form-control:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
      }
      
      .btn-primary {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        border: none;
        border-radius: 10px;
        padding: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
      }
      
      .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(99, 102, 241, 0.2);
      }
      
      .btn-warning {
        background: linear-gradient(135deg, var(--warning-color), #f97316);
        border: none;
        border-radius: 10px;
        padding: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
      }
      
      .btn-warning:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(245, 158, 11, 0.2);
      }
      
      .alert {
        border-radius: 10px;
        border: none;
        padding: 15px;
        margin-bottom: 20px;
      }
      
      .loading-spinner {
        display: none;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 1s ease-in-out infinite;
        margin-right: 10px;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      .form-text {
        font-size: 0.85rem;
        color: #6b7280;
        margin-top: 5px;
      }
      
      .email-validation {
        display: flex;
        align-items: center;
        margin-top: 5px;
        font-size: 0.85rem;
      }
      
      .email-validation i {
        margin-right: 5px;
      }
      
      .valid-email {
        color: var(--success-color);
      }
      
      .invalid-email {
        color: var(--danger-color);
      }
      
      .feature-list {
        list-style: none;
        padding: 0;
        margin: 20px 0;
      }
      
      .feature-list li {
        padding: 8px 0;
        display: flex;
        align-items: center;
      }
      
      .feature-list i {
        color: var(--primary-color);
        margin-right: 10px;
      }
      
      .auth-footer {
        text-align: center;
        padding: 20px;
        color: #6b7280;
        font-size: 0.85rem;
      }
    </style>
  </head>
  <body>
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <h1><i class="fas fa-shield-alt me-2"></i>SecureAuth</h1>
          <p>Your trusted authentication partner</p>
        </div>
        
        <div class="auth-tabs">
          <button class="auth-tab active" id="register-tab" onclick="switchTab('register')">
            <i class="fas fa-user-plus me-2"></i>Register
          </button>
          <button class="auth-tab" id="forgot-tab" onclick="switchTab('forgot')">
            <i class="fas fa-key me-2"></i>Reset Password
          </button>
        </div>
        
        <div class="auth-body">
          {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
              {% for category, msg in messages %}
                <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show" role="alert">
                  <i class="fas fa-{{ 'exclamation-circle' if category == 'error' else 'check-circle' }} me-2"></i>
                  {{ msg }}
                  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
              {% endfor %}
            {% endif %}
          {% endwith %}
          
          <!-- Register Form -->
          <div id="register-form">
            <h4 class="mb-4">Create Your Account</h4>
            <p class="text-muted mb-4">Join us today and get instant access to all features.</p>
            
            <ul class="feature-list">
              <li><i class="fas fa-check-circle"></i> Secure account creation</li>
              <li><i class="fas fa-check-circle"></i> Instant credentials delivery</li>
              <li><i class="fas fa-check-circle"></i> Password encryption</li>
            </ul>
            
            <form method="post" action="{{ url_for('register') }}" id="reg-form">
              <div class="mb-3">
                <label for="regEmail" class="form-label">Email address</label>
                <input type="email" class="form-control" id="regEmail" name="email" placeholder="Enter your email" required>
                <div class="email-validation" id="email-validation">
                  <i class="fas fa-info-circle"></i>
                  <span>Please enter a valid email address</span>
                </div>
              </div>
              <button type="submit" class="btn btn-primary w-100">
                <span class="loading-spinner" id="reg-loading"></span>
                <i class="fas fa-user-plus me-2"></i>Create Account
              </button>
            </form>
          </div>
          
          <!-- Forgot Password Form -->
          <div id="forgot-form" style="display: none;">
            <h4 class="mb-4">Reset Your Password</h4>
            <p class="text-muted mb-4">Enter your email address and we'll send you new credentials.</p>
            
            <ul class="feature-list">
              <li><i class="fas fa-check-circle"></i> Secure password reset</li>
              <li><i class="fas fa-check-circle"></i> New credentials delivery</li>
              <li><i class="fas fa-check-circle"></i> Email verification</li>
            </ul>
            
            <form method="post" action="{{ url_for('forgot') }}" id="forgot-form-element">
              <div class="mb-3">
                <label for="forgotEmail" class="form-label">Email address</label>
                <input type="email" class="form-control" id="forgotEmail" name="email" placeholder="Enter your registered email" required>
                <div class="email-validation" id="forgot-email-validation">
                  <i class="fas fa-info-circle"></i>
                  <span>Please enter a valid email address</span>
                </div>
              </div>
              <button type="submit" class="btn btn-warning w-100">
                <span class="loading-spinner" id="forgot-loading"></span>
                <i class="fas fa-key me-2"></i>Reset Password
              </button>
            </form>
          </div>
        </div>
        
        <div class="auth-footer">
          <p>&copy; 2023 SecureAuth. All rights reserved.</p>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
      function switchTab(tab) {
        const registerTab = document.getElementById('register-tab');
        const forgotTab = document.getElementById('forgot-tab');
        const registerForm = document.getElementById('register-form');
        const forgotForm = document.getElementById('forgot-form');
        
        if (tab === 'register') {
          registerTab.classList.add('active');
          forgotTab.classList.remove('active');
          registerForm.style.display = 'block';
          forgotForm.style.display = 'none';
        } else {
          registerTab.classList.remove('active');
          forgotTab.classList.add('active');
          registerForm.style.display = 'none';
          forgotForm.style.display = 'block';
        }
      }
      
      // Email validation
      document.getElementById('regEmail').addEventListener('input', function() {
        validateEmail(this, 'email-validation');
      });
      
      document.getElementById('forgotEmail').addEventListener('input', function() {
        validateEmail(this, 'forgot-email-validation');
      });
      
      function validateEmail(input, validationId) {
        const validation = document.getElementById(validationId);
        const email = input.value;
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        
        if (email === '') {
          validation.innerHTML = '<i class="fas fa-info-circle"></i><span>Please enter a valid email address</span>';
          validation.className = 'email-validation';
        } else if (emailRegex.test(email)) {
          validation.innerHTML = '<i class="fas fa-check-circle"></i><span>Valid email address</span>';
          validation.className = 'email-validation valid-email';
        } else {
          validation.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>Invalid email format</span>';
          validation.className = 'email-validation invalid-email';
        }
      }
      
      // Form submission with loading state
      document.getElementById('reg-form').addEventListener('submit', function() {
        document.getElementById('reg-loading').style.display = 'inline-block';
      });
      
      document.getElementById('forgot-form-element').addEventListener('submit', function() {
        document.getElementById('forgot-loading').style.display = 'inline-block';
      });
    </script>
  </body>
</html>
"""

# ---------------- Flask Routes ----------------
@app.route('/')
def home():
    return render_template_string(INDEX_HTML)

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email').strip().lower()
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('home'))
    
    if not validate_email(email):
        flash('Please enter a valid email address', 'error')
        return redirect(url_for('home'))

    if user_exists(email):
        flash('Email already registered', 'error')
        return redirect(url_for('home'))

    user_id, password = generate_credentials()
    password_hash = generate_password_hash(password)
    try:
        if save_user(email, password_hash, user_id):
            subject = 'Welcome to SecureAuth - Your Account Credentials'
            
            # Using an f-string for the email body to fix the formatting error
            email_body_html = f"""
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Welcome to SecureAuth</title>
    <style>
      img {{ border: none; -ms-interpolation-mode: bicubic; max-width: 100%; }}
      body {{ background-color: #f4f5f6; font-family: Arial, sans-serif; -webkit-font-smoothing: antialiased; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; }}
      table {{ border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; }}
      table td {{ font-family: Arial, sans-serif; font-size: 14px; vertical-align: top; }}
      .body {{ background-color: #f4f5f6; width: 100%; }}
      .container {{ display: block; margin: 0 auto !important; max-width: 580px; padding: 10px; width: 580px; }}
      .content {{ box-sizing: border-box; display: block; margin: 0 auto; max-width: 580px; padding: 10px; }}
      .main {{ background: #ffffff; border-radius: 8px; width: 100%; }}
      .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 20px 30px; border-radius: 8px 8px 0 0; color: white; text-align: center; }}
      .footer {{ clear: both; padding-top: 10px; text-align: center; width: 100%; }}
      .footer td, .footer p, .footer span, .footer a {{ color: #999999; font-size: 12px; text-align: center; }}
      h1 {{ color: #222222; font-family: Arial, sans-serif; font-size: 28px; font-weight: Bold; margin-top: 0; text-align: center; }}
      h2 {{ color: #222222; font-family: Arial, sans-serif; font-size: 22px; font-weight: Bold; margin-top: 0; margin-bottom: 15px; }}
      p {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; margin-bottom: 15px; }}
      .credential-box {{ background: #f8f9fa; border-left: 4px solid #6366f1; padding: 15px 20px; margin: 20px 0; }}
      .credential-label {{ font-weight: bold; color: #555; font-size: 12px; text-transform: uppercase; }}
      .credential-value {{ font-family: monospace; font-size: 18px; color: #000; background: #e9ecef; padding: 10px; border-radius: 4px; word-break: break-all; }}
    </style>
  </head>
  <body class="">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td>&nbsp;</td>
        <td class="container">
          <div class="content">
            <table class="main">
              <tr>
                <td class="header">
                  <h1>SecureAuth</h1>
                  <p>Your account is ready!</p>
                </td>
              </tr>
              <tr>
                <td class="content-wrap">
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td class="content-block">
                        <h2>Welcome!</h2>
                        <p>Thank you for registering. Your account has been successfully created. Please find your login credentials below.</p>
                      </td>
                    </tr>
                    <tr>
                      <td class="content-block">
                        <div class="credential-box">
                          <div class="credential-label">User ID</div>
                          <div class="credential-value">{user_id}</div>
                        </div>
                        <div class="credential-box">
                          <div class="credential-label">Password</div>
                          <div class="credential-value">{password}</div>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td class="content-block">
                        <p>For your security, please change your password after your first login.</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            <div class="footer">
              <table border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td class="content-block">
                    <span class="apple-link">SecureAuth Inc.</span>
                    <br>Don't reply to this email.
                  </td>
                </tr>
              </table>
            </div>
          </div>
        </td>
        <td>&nbsp;</td>
      </tr>
    </table>
  </body>
</html>
            """
            if send_email(email, subject, email_body_html, is_html=True):
                flash('Registered successfully! Check your email for credentials.', 'success')
            else:
                flash('Error sending email. Please try again.', 'error')
        else:
            flash('Error creating account. Please try again.', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('home'))

@app.route('/forgot', methods=['POST'])
def forgot():
    email = request.form.get('email').strip().lower()
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('home'))
    
    if not validate_email(email):
        flash('Please enter a valid email address', 'error')
        return redirect(url_for('home'))

    uid = user_exists(email)
    if not uid:
        flash('Email not found', 'error')
        return redirect(url_for('home'))

    new_user_id, new_password = generate_credentials()
    new_hash = generate_password_hash(new_password)
    try:
        if update_password(email, new_hash):
            subject = 'SecureAuth - Your Password Has Been Reset'
            
            # Using an f-string for the email body to fix the formatting error
            email_body_html = f"""
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Password Reset - SecureAuth</title>
    <style>
      img {{ border: none; -ms-interpolation-mode: bicubic; max-width: 100%; }}
      body {{ background-color: #f4f5f6; font-family: Arial, sans-serif; -webkit-font-smoothing: antialiased; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; }}
      table {{ border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; }}
      table td {{ font-family: Arial, sans-serif; font-size: 14px; vertical-align: top; }}
      .body {{ background-color: #f4f5f6; width: 100%; }}
      .container {{ display: block; margin: 0 auto !important; max-width: 580px; padding: 10px; width: 580px; }}
      .content {{ box-sizing: border-box; display: block; margin: 0 auto; max-width: 580px; padding: 10px; }}
      .main {{ background: #ffffff; border-radius: 8px; width: 100%; }}
      .header {{ background: linear-gradient(135deg, #f59e0b, #f97316); padding: 20px 30px; border-radius: 8px 8px 0 0; color: white; text-align: center; }}
      .footer {{ clear: both; padding-top: 10px; text-align: center; width: 100%; }}
      .footer td, .footer p, .footer span, .footer a {{ color: #999999; font-size: 12px; text-align: center; }}
      h1 {{ color: #222222; font-family: Arial, sans-serif; font-size: 28px; font-weight: Bold; margin-top: 0; text-align: center; }}
      h2 {{ color: #222222; font-family: Arial, sans-serif; font-size: 22px; font-weight: Bold; margin-top: 0; margin-bottom: 15px; }}
      p {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; margin-bottom: 15px; }}
      .credential-box {{ background: #f8f9fa; border-left: 4px solid #f59e0b; padding: 15px 20px; margin: 20px 0; }}
      .credential-label {{ font-weight: bold; color: #555; font-size: 12px; text-transform: uppercase; }}
      .credential-value {{ font-family: monospace; font-size: 18px; color: #000; background: #e9ecef; padding: 10px; border-radius: 4px; word-break: break-all; }}
      .alert {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; border-radius: 5px; }}
      .alert h4 {{ margin-top: 0; color: #991b1b; }}
    </style>
  </head>
  <body class="">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td>&nbsp;</td>
        <td class="container">
          <div class="content">
            <table class="main">
              <tr>
                <td class="header">
                  <h1>SecureAuth</h1>
                  <p>Password Reset Request</p>
                </td>
              </tr>
              <tr>
                <td class="content-wrap">
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td class="content-block">
                        <h2>Password Reset</h2>
                        <p>We received a request to reset your password. Your credentials have been successfully reset. Below are your new login details:</p>
                      </td>
                    </tr>
                    <tr>
                      <td class="content-block">
                        <div class="alert">
                          <h4>Important</h4>
                          <p>If you didn't request this password reset, please contact our support team immediately.</p>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td class="content-block">
                        <div class="credential-box">
                          <div class="credential-label">New User ID</div>
                          <div class="credential-value">{new_user_id}</div>
                        </div>
                        <div class="credential-box">
                          <div class="credential-label">New Password</div>
                          <div class="credential-value">{new_password}</div>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td class="content-block">
                        <p>For your security, please change your password after your first login.</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            <div class="footer">
              <table border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td class="content-block">
                    <span class="apple-link">SecureAuth Inc.</span>
                    <br>Don't reply to this email.
                  </td>
                </tr>
              </table>
            </div>
          </div>
        </td>
        <td>&nbsp;</td>
      </tr>
    </table>
  </body>
</html>
            """
            if send_email(email, subject, email_body_html, is_html=True):
                flash('Password reset successful! Check your email for new credentials.', 'success')
            else:
                flash('Error sending email. Please try again.', 'error')
        else:
            flash('Error resetting password. Please try again.', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')

    return redirect(url_for('home'))

# ---------------- Signal Handlers for Graceful Shutdown ----------------
def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ---------------- Run App ----------------
if __name__ == '__main__':
    # Default port
    port = 5000
    
    # Check if default port is in use
    if is_port_in_use(port):
        print(f"Port {port} is already in use. Finding an available port...")
        port = find_free_port()
        print(f"Using port {port} instead.")
    
    print(f"Starting Flask app on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the server")
    
    try:
        app.run(host='127.0.0.1', port=port, debug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Trying to start with a different port...")
        port = find_free_port()
        print(f"Starting Flask app on http://127.0.0.1:{port}")
        app.run(host='127.0.0.1', port=port, debug=True)
