from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import os
from dotenv import load_dotenv
import markdown
import re
import time
import secrets
import sqlite3
from datetime import datetime, date, timedelta
from urllib.parse import quote
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from io import BytesIO
from html import unescape

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

print(f"✓ Using Assistant: {ASSISTANT_ID}")

# Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists('/home/VihaanAgrawal'):
    DB_PATH = '/home/VihaanAgrawal/emerald-counselor-ai/users.db'
else:
    DB_PATH = os.path.join(BASE_DIR, 'users.db')

# Rate limit settings
MESSAGES_PER_DAY = 20

def normalize_date(value):
    """Normalize stored date/datetime values to YYYY-MM-DD for comparison."""
    if not value:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value)
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        # Fallback for non-ISO strings like "YYYY-MM-DD HH:MM:SS"
        return text[:10] if len(text) >= 10 else text

# PDF documents directory
PDF_DIR = os.path.join(os.path.dirname(__file__), 'school_documents')

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, class_of, thread_id, messages_today=0, last_message_date=None, tutorial_completed=0, display_name=None, current_grade=None, bio=None):
        self.id = id
        self.username = username
        self.class_of = class_of
        self.thread_id = thread_id
        self.messages_today = messages_today
        self.last_message_date = last_message_date
        self.tutorial_completed = tutorial_completed
        self.display_name = display_name
        self.current_grade = current_grade
        self.bio = bio

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, username, class_of, thread_id, messages_today, last_message_date, tutorial_completed FROM users WHERE id = ?', (user_id,))
    except sqlite3.OperationalError:
        # Fallback for databases without tutorial_completed column
        cursor.execute('SELECT id, username, class_of, thread_id, messages_today, last_message_date FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        if len(user_data) >= 7:
            return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4] or 0, user_data[5], user_data[6] or 0)
        else:
            return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4] or 0, user_data[5], 0)
    return None

def process_citations(text):
    """Remove citation markers from text"""
    citation_pattern = r'【\d+:\d+†[^】]+】'
    text = re.sub(citation_pattern, '', text)
    return text

def extract_file_ids_from_message(message):
    """Extract file IDs from OpenAI message annotations"""
    file_ids = set()
    try:
        if hasattr(message, 'content') and message.content:
            for content_item in message.content:
                if hasattr(content_item, 'text') and content_item.text:
                    text_obj = content_item.text
                    # Check for annotations attribute
                    if hasattr(text_obj, 'annotations') and text_obj.annotations:
                        for annotation in text_obj.annotations:
                            # Try file_path.file_id (newer API format for file_search)
                            if hasattr(annotation, 'file_path'):
                                file_path_obj = annotation.file_path
                                if file_path_obj:
                                    if hasattr(file_path_obj, 'file_id'):
                                        file_id = file_path_obj.file_id
                                        file_ids.add(file_id)
                                        print(f"Found file_id via file_path: {file_id}")
                                    # Also try accessing as dict-like
                                    elif isinstance(file_path_obj, dict) and 'file_id' in file_path_obj:
                                        file_id = file_path_obj['file_id']
                                        file_ids.add(file_id)
                                        print(f"Found file_id via file_path (dict): {file_id}")
                            # Try direct file_id attribute
                            if hasattr(annotation, 'file_id'):
                                file_id = annotation.file_id
                                if file_id:
                                    file_ids.add(file_id)
                                    print(f"Found file_id directly: {file_id}")
                            # Try as dict-like object
                            if isinstance(annotation, dict):
                                if 'file_path' in annotation and annotation['file_path']:
                                    if 'file_id' in annotation['file_path']:
                                        file_id = annotation['file_path']['file_id']
                                        file_ids.add(file_id)
                                        print(f"Found file_id via dict file_path: {file_id}")
                                if 'file_id' in annotation:
                                    file_id = annotation['file_id']
                                    if file_id:
                                        file_ids.add(file_id)
                                        print(f"Found file_id via dict: {file_id}")
        print(f"Extracted {len(file_ids)} file IDs: {file_ids}")
    except Exception as e:
        print(f"Error extracting file IDs: {e}")
        import traceback
        traceback.print_exc()
    return file_ids

def get_filename_from_file_id(file_id):
    """Get local filename from OpenAI file ID"""
    try:
        file_info = client.files.retrieve(file_id)
        openai_filename = file_info.filename
        # Map OpenAI filename to local filename
        # OpenAI might have different naming, so we try to match
        local_files = os.listdir(PDF_DIR)
        for local_file in local_files:
            if local_file.endswith('.pdf'):
                # Simple matching - check if OpenAI filename matches or is similar
                if openai_filename.lower() in local_file.lower() or local_file.lower() in openai_filename.lower():
                    return local_file
        # If no match found, return OpenAI filename
        return openai_filename
    except Exception as e:
        print(f"Error getting filename for file_id {file_id}: {e}")
        return None

def check_and_update_rate_limit(user_id, username):
    """Check if user has exceeded rate limit and update count"""
    # Special user "Vihaan Agrawal" has unlimited messages
    if username == "Vihaan Agrawal":
        return True, 0  # Always allowed, return 0 for count (unlimited)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get user's message count and last message date
    cursor.execute('SELECT messages_today, last_message_date FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()

    messages_today = result[0] or 0
    last_message_date = result[1]
    today = date.today().isoformat()
    last_date = normalize_date(last_message_date)

    # Reset count if it's a new day
    if last_date != today:
        messages_today = 0
        cursor.execute('UPDATE users SET messages_today = ?, last_message_date = ? WHERE id = ?',
                       (0, today, user_id))
        conn.commit()

    # Check if user has exceeded limit
    if messages_today >= MESSAGES_PER_DAY:
        conn.close()
        return False, messages_today

    # Increment message count
    messages_today += 1
    cursor.execute('UPDATE users SET messages_today = ?, last_message_date = ? WHERE id = ?',
                   (messages_today, today, user_id))
    conn.commit()
    conn.close()

    if current_user.is_authenticated and current_user.id == user_id:
        current_user.messages_today = messages_today
        current_user.last_message_date = today

    return True, messages_today

def get_rate_limit_status(user_id, username):
    """Return remaining messages and ensure daily reset is persisted."""
    if username == "Vihaan Agrawal":
        return {'remaining': 'unlimited', 'is_unlimited': True}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT messages_today, last_message_date FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    today = date.today().isoformat()

    messages_today = (result[0] if result else 0) or 0
    last_message_date = result[1] if result else None
    last_date = normalize_date(last_message_date)

    if last_date != today:
        messages_today = 0
        cursor.execute('UPDATE users SET messages_today = ?, last_message_date = ? WHERE id = ?',
                       (0, today, user_id))
        conn.commit()

    conn.close()
    remaining = max(MESSAGES_PER_DAY - messages_today, 0)
    return {'remaining': remaining, 'is_unlimited': False}

@app.route('/')
@login_required
def home():
    # Calculate remaining messages (unlimited for "Vihaan Agrawal")
    rate_status = get_rate_limit_status(current_user.id, current_user.username)
    remaining = rate_status['remaining']
    is_unlimited = rate_status['is_unlimited']

    # Get profile and tutorial info
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT tutorial_completed, display_name, current_grade, bio FROM users WHERE id = ?', (current_user.id,))
        result = cursor.fetchone()
        tutorial_completed = result[0] if result and result[0] is not None else 0
        display_name = result[1] if result and result[1] else None
        current_grade = result[2] if result and result[2] else None
        bio = result[3] if result and result[3] else None
    except sqlite3.OperationalError:
        # Columns don't exist yet
        tutorial_completed = 0
        display_name = None
        current_grade = None
        bio = None
    conn.close()

    return render_template('index.html',
                         username=current_user.username,
                         class_of=current_user.class_of,
                         messages_remaining=remaining,
                         is_unlimited=is_unlimited,
                         tutorial_completed=tutorial_completed,
                         display_name=display_name,
                         current_grade=current_grade,
                         bio=bio)

@app.route('/get_history', methods=['GET'])
@login_required
def get_history():
    """Load previous chat messages for this user"""
    try:
        thread_id = current_user.thread_id

        if not thread_id:
            # No previous conversation
            return jsonify({'messages': []})

        # Get all messages from the thread
        messages = client.beta.threads.messages.list(
            thread_id=thread_id,
            order='asc',  # Oldest first
            limit=100  # Get last 100 messages
        )

        # Format messages for display
        chat_history = []
        for msg in messages.data:
            role = msg.role  # 'user' or 'assistant'
            content = msg.content[0].text.value

            # Remove user context from user messages
            if role == 'user' and '[User Context:' in content:
                # Extract just the student question
                parts = content.split('Student Question: ')
                if len(parts) > 1:
                    content = parts[1]

            # Remove citations from assistant messages
            if role == 'assistant':
                content = process_citations(content)

            # Convert markdown to HTML for assistant messages
            if role == 'assistant':
                content = markdown.markdown(
                    content,
                    extensions=['fenced_code', 'codehilite', 'nl2br', 'tables', 'sane_lists']
                )
            else:
                # For user messages, convert newlines to <br>
                content = content.replace('\n', '<br>')

            chat_history.append({
                'role': role,
                'content': content
            })

        return jsonify({'messages': chat_history})

    except Exception as e:
        print(f"Error loading history: {e}")
        return jsonify({'messages': []})

@app.route('/get_remaining_messages', methods=['GET'])
@login_required
def get_remaining_messages():
    """Get remaining messages for current user"""
    rate_status = get_rate_limit_status(current_user.id, current_user.username)
    return jsonify(rate_status)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash, class_of, thread_id, messages_today, last_message_date FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[3], user_data[4], user_data[5] or 0, user_data[6])
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        class_of = request.form.get('class_of')

        if len(username) < 3:
            return render_template('signup.html', error='Username must be at least 3 characters')

        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')

        # Check if passwords match
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')

        # Get IP address for logging only (no per-device signup limit)
        ip_address = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()

        password_hash = generate_password_hash(password)

        try:
            for attempt in range(1, 4):
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10.0)
                    cursor = conn.cursor()
                    cursor.execute('PRAGMA journal_mode=WAL')
                    cursor.execute('PRAGMA busy_timeout=30000')
                    cursor.execute(
                        'INSERT INTO users (username, password_hash, class_of, messages_today, last_message_date, ip_address) VALUES (?, ?, ?, 0, ?, ?)',
                        (username, password_hash, class_of, str(date.today()), ip_address)
                    )
                    user_id = cursor.lastrowid
                    conn.commit()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < 3:
                        time.sleep(0.5 * attempt)
                        continue
                    raise
                finally:
                    if 'conn' in locals():
                        conn.close()

            # Get tutorial_completed status (default to 0 for new users)
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('SELECT tutorial_completed FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            tutorial_completed = result[0] if result and len(result) > 0 and result[0] is not None else 0

            # Auto-login the user after signup
            user = User(user_id, username, class_of, None, 0, str(date.today()), tutorial_completed)
            login_user(user)
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            return render_template('signup.html', error='Username already exists')
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return render_template('signup.html', error='Database is busy. Please try again in a moment.')
            raise

    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    """Download PDF file with authentication"""
    # Security: prevent directory traversal
    filename = os.path.basename(filename)
    
    # Check if file exists
    file_path = os.path.join(PDF_DIR, filename)
    
    if not os.path.exists(file_path) or not filename.endswith('.pdf'):
        abort(404)
    
    # Send file
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/download_chat', methods=['POST'])
@login_required
def download_chat():
    """Generate and download selected chat messages as PDF"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'No messages selected'}), 400
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor='#1b5e20',
            spaceAfter=12,
        )
        user_style = ParagraphStyle(
            'UserMessage',
            parent=styles['BodyText'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            textColor='#1976d2',
            spaceAfter=12,
            spaceBefore=6,
        )
        bot_style = ParagraphStyle(
            'BotMessage',
            parent=styles['BodyText'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            textColor='#1b5e20',
            spaceAfter=12,
            spaceBefore=6,
        )
        
        # Add title
        title = Paragraph(f"Chat Export - {current_user.username}<br/>Emerald High School Counselor Assistant", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Add messages
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            # Clean HTML tags and decode entities
            content = re.sub(r'<[^>]+>', '', content)  # Remove HTML tags
            content = unescape(content)  # Decode HTML entities
            content = content.replace('\n', '<br/>')  # Preserve line breaks
            
            if role == 'user':
                label = f"<b>You:</b><br/>{content}"
                p = Paragraph(label, user_style)
            else:
                label = f"<b>AI Counselor:</b><br/>{content}"
                p = Paragraph(label, bot_style)
            
            elements.append(p)
            elements.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'chat_export_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error generating PDF'}), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get('message', '')

    print(f"\n[{current_user.username}] sent: {user_message}")

    # Check rate limit
    allowed, count = check_and_update_rate_limit(current_user.id, current_user.username)

    if not allowed:
        return jsonify({
            'response': f'<p><strong>Daily message limit reached!</strong></p><p>You\'ve used all {MESSAGES_PER_DAY} messages for today. Your limit will reset tomorrow.</p><p>If you need more assistance, please contact your school counselor directly.</p>',
            'limit_reached': True
        })

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get thread_id and thread_created_at for this user's conversation
        cursor.execute('SELECT thread_id, thread_created_at FROM users WHERE id = ?', (current_user.id,))
        result = cursor.fetchone()
        thread_id = result[0] if result else None
        thread_created_at = result[1] if result and result[1] else None
        
        # Check if thread exists and is older than 7 days (each conversation gets 7 days from creation)
        should_create_new_thread = False
        if thread_id:
            if thread_created_at:
                # Parse the timestamp and check if this conversation is older than 7 days
                created_time = datetime.fromisoformat(thread_created_at)
                if datetime.now() - created_time > timedelta(days=7):
                    # Delete old thread from OpenAI (this conversation expired after 7 days)
                    try:
                        client.beta.threads.delete(thread_id=thread_id)
                        print(f"Deleted expired thread {thread_id} for {current_user.username} (older than 7 days)")
                    except Exception as e:
                        print(f"Error deleting thread {thread_id}: {e}")
                    should_create_new_thread = True
                else:
                    # Thread is still valid (less than 7 days old) - reuse it to maintain memory
                    print(f"Reusing existing thread {thread_id} for {current_user.username} (memory preserved)")
            else:
                # Thread exists but no timestamp - initialize timestamp instead of deleting
                # This handles threads created before the migration
                now = datetime.now().isoformat()
                cursor.execute('UPDATE users SET thread_created_at = ? WHERE id = ?', (now, current_user.id))
                conn.commit()
                print(f"Initialized timestamp for existing thread {thread_id} for {current_user.username}")
        else:
            should_create_new_thread = True
        
        # Create new thread/conversation if needed (each gets its own 7-day timer)
        if should_create_new_thread:
            thread = client.beta.threads.create()
            thread_id = thread.id
            now = datetime.now().isoformat()
            
            cursor.execute('UPDATE users SET thread_id = ?, thread_created_at = ? WHERE id = ?', 
                         (thread_id, now, current_user.id))
            conn.commit()
            
            current_user.thread_id = thread_id
            print(f"Created new conversation thread for {current_user.username}: {thread_id} (expires in 7 days)")
        
        conn.close()

        # Get user profile info for context
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        display_name = None
        current_grade = None
        bio = None
        
        try:
            cursor.execute('SELECT display_name, current_grade, bio FROM users WHERE id = ?', (current_user.id,))
            profile = cursor.fetchone()
            if profile:
                display_name = profile[0] if profile[0] else None
                current_grade = profile[1] if profile[1] else None
                bio = profile[2] if profile[2] else None
        except sqlite3.OperationalError:
            # Profile columns don't exist yet - use defaults
            pass
        
        conn.close()
        
        # Build context string
        context_parts = [f"Username: {current_user.username}", f"Graduation Year: Class of {current_user.class_of}"]
        if display_name and display_name != current_user.username:
            context_parts.append(f"Display Name: {display_name}")
        if current_grade:
            context_parts.append(f"Current Grade: {current_grade}")
        if bio:
            context_parts.append(f"Bio/Interests: {bio}")
        
        context_str = ", ".join(context_parts)
        contextual_message = f"""[User Context: {context_str}]

Student Question: {user_message}"""

        # Add message with context
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=contextual_message
        )

        # Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Wait for completion
        while run.status in ['queued', 'in_progress']:
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        # Check if file_search was used by examining run steps
        file_search_used = False
        try:
            run_steps = client.beta.threads.runs.steps.list(
                thread_id=thread_id,
                run_id=run.id
            )
            print(f"Checking {len(run_steps.data)} run steps for file_search calls...")
            for step_idx, step in enumerate(run_steps.data):
                print(f"Step {step_idx}: type={getattr(step, 'type', 'unknown')}")
                if hasattr(step, 'step_details') and step.step_details:
                    step_details = step.step_details
                    print(f"  Step details type: {type(step_details)}")
                    print(f"  Step details attributes: {dir(step_details)}")
                    # Check for tool_calls in step_details
                    if hasattr(step_details, 'tool_calls') and step_details.tool_calls:
                        print(f"  Found {len(step_details.tool_calls)} tool calls")
                        for tool_idx, tool_call in enumerate(step_details.tool_calls):
                            # Debug: print tool_call structure
                            tool_type = getattr(tool_call, 'type', None)
                            print(f"    Tool call {tool_idx}: type={tool_type}, attributes: {[a for a in dir(tool_call) if not a.startswith('_')]}")
                            # Check if this is a file_search call
                            if tool_type == 'file_search':
                                file_search_used = True
                                print(f"    ✓ Found file_search tool call - documents were referenced")
                                break
                    else:
                        print(f"  No tool_calls found in step_details")
                    if file_search_used:
                        break
        except Exception as e:
            print(f"Error checking run steps: {e}")

        # Note: file_search doesn't tell us which specific files were used
        # We can only show source links if we can extract specific file IDs from annotations
        # For now, we won't show links when only file_search is used (since it searches all files)
        file_ids = set()

        # Get response
        messages = client.beta.threads.messages.list(
            thread_id=thread_id,
            order='desc',
            limit=1
        )

        message = messages.data[0]
        bot_response_text = message.content[0].text.value
        bot_response_text = process_citations(bot_response_text)

        print(f"Assistant responded: {bot_response_text[:100]}...")

        # Extract file IDs from message annotations (these would be specific files if available)
        file_ids_from_annotations = extract_file_ids_from_message(message)
        file_ids.update(file_ids_from_annotations)

        # Only show source links if we have specific file IDs from annotations
        # (Not showing all files from vector store since file_search doesn't specify which were used)
        download_links_html = ""
        if file_ids:
            download_links_html = '<div style="margin-top: 15px; padding: 10px; background-color: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;"><strong>📄 Source Documents:</strong><ul style="margin: 8px 0 0 0; padding-left: 20px;">'
            for file_id in file_ids:
                filename = get_filename_from_file_id(file_id)
                print(f"Mapping file_id {file_id} to filename: {filename}")
                if filename:
                    # URL encode the filename
                    encoded_filename = quote(filename)
                    download_links_html += f'<li><a href="/download/{encoded_filename}" class="pdf-download-link" data-filename="{filename}" style="color: #1976d2; text-decoration: underline;">📥 {filename}</a></li>'
            download_links_html += '</ul></div>'
        else:
            print("No file IDs found in message annotations")

        # Convert markdown to HTML
        bot_response = markdown.markdown(
            bot_response_text,
            extensions=['fenced_code', 'codehilite', 'nl2br', 'tables', 'sane_lists']
        )

        # Add download links if available
        if download_links_html:
            bot_response += download_links_html

        # Add remaining messages info
        remaining = MESSAGES_PER_DAY - count
        if remaining <= 3:
            bot_response += f'<p style="margin-top: 15px; font-size: 12px; opacity: 0.7;"><em>💬 {remaining} messages remaining today</em></p>'

        return jsonify({'response': bot_response})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': 'Sorry, I encountered an error. Please try again.'})

@app.route('/complete_tutorial', methods=['POST'])
@login_required
def complete_tutorial():
    """Mark tutorial as completed for the current user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET tutorial_completed = 1 WHERE id = ?', (current_user.id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.OperationalError:
        # Column doesn't exist yet - silently fail
        return jsonify({'success': False, 'error': 'Tutorial tracking not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT display_name, current_grade, bio FROM users WHERE id = ?', (current_user.id,))
            result = cursor.fetchone()
            display_name = result[0] if result and result[0] else None
            current_grade = result[1] if result and result[1] else None
            bio = result[2] if result and result[2] else None
        except sqlite3.OperationalError:
            # Columns don't exist yet - return None for all
            display_name = None
            current_grade = None
            bio = None
        conn.close()
        
        return jsonify({
            'display_name': display_name,
            'current_grade': current_grade,
            'bio': bio,
            'username': current_user.username,
            'class_of': current_user.class_of
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        display_name = data.get('display_name', '').strip()
        current_grade = data.get('current_grade')
        bio = data.get('bio', '').strip()
        
        # Validate current_grade if provided (should be 9-12)
        if current_grade is not None and current_grade not in [9, 10, 11, 12]:
            return jsonify({'error': 'Current grade must be 9, 10, 11, or 12'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Update profile fields (set to NULL if empty string)
            cursor.execute('''UPDATE users 
                             SET display_name = ?, current_grade = ?, bio = ? 
                             WHERE id = ?''',
                         (display_name if display_name else None, 
                          current_grade if current_grade else None,
                          bio if bio else None,
                          current_user.id))
            conn.commit()
        except sqlite3.OperationalError as e:
            conn.close()
            if 'no such column' in str(e).lower():
                return jsonify({'error': 'Profile fields not available. Please run the migration script: python migration_add_profile_fields.py'}), 500
            raise
        conn.close()
        
        # Update current_user object
        current_user.display_name = display_name if display_name else None
        current_user.current_grade = current_grade if current_grade else None
        current_user.bio = bio if bio else None
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False)