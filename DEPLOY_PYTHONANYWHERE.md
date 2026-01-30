# Deploying to PythonAnywhere

## Step 1: Create PythonAnywhere Account
1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Sign up for a free account (or paid if you need more features)
3. Log into your account

## Step 2: Upload Your Files

### Option A: Using the Files Tab (Web Interface)
1. Click on the **Files** tab
2. Navigate to `/home/yourusername/` (replace `yourusername` with your PythonAnywhere username)
3. Create a folder: `emerald-counselor-ai`
4. Upload all your files:
   - `main.py`
   - `requirements.txt`
   - All files from `templates/` folder
   - All files from `static/` folder
   - All PDFs from `school_documents/` folder
   - Migration scripts (optional, but recommended)

### Option B: Using Git (Recommended)
1. Push your code to GitHub/GitLab
2. In PythonAnywhere, open a Bash console
3. Run:
   ```bash
   cd ~
   git clone https://github.com/yourusername/your-repo-name.git emerald-counselor-ai
   cd emerald-counselor-ai
   ```

## Step 3: Set Up Python Environment

1. Open a **Bash console** in PythonAnywhere
2. Navigate to your project:
   ```bash
   cd ~/emerald-counselor-ai
   ```
3. Create a virtual environment (if using Python 3.10+):
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   ```
   OR use the system Python (free accounts):
   ```bash
   # Free accounts typically use Python 3.9 or 3.10
   # You'll install packages globally (which is fine for free accounts)
   ```

4. Install dependencies:
   ```bash
   pip3.10 install --user -r requirements.txt
   ```
   (Use `pip3.9` if you're on Python 3.9, or just `pip3 install --user`)

## Step 4: Set Environment Variables

1. In PythonAnywhere, go to the **Web** tab
2. Click on your web app (or create a new one)
3. Scroll down to **Environment variables**
4. Add these three variables:
   - `SECRET_KEY`: Generate a random secret key (you can use: `python3 -c "import secrets; print(secrets.token_hex(32))"`)
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `OPENAI_ASSISTANT_ID`: Your OpenAI Assistant ID

**OR** create a `.env` file in your project directory:
```bash
cd ~/emerald-counselor-ai
nano .env
```

Add:
```
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
OPENAI_ASSISTANT_ID=your-assistant-id
```

## Step 5: Update Database Path in main.py

The code already checks for PythonAnywhere path, but make sure it matches your username:
```python
if os.path.exists('/home/yourusername'):  # Replace 'yourusername' with your actual username
    DB_PATH = '/home/yourusername/emerald-counselor-ai/users.db'
```

## Step 6: Initialize Database

1. Open a Bash console
2. Run:
   ```bash
   cd ~/emerald-counselor-ai
   python3.10 init_db.py
   ```
3. Run migrations (if needed):
   ```bash
   python3.10 migration_add_ip_tracking.py
   python3.10 migration_add_thread_timestamp.py  # If this file exists
   python3.10 migration_add_tutorial_tracking.py
   ```

## Step 7: Create WSGI File

1. Go to the **Web** tab in PythonAnywhere
2. Click on your web app
3. Click on **WSGI configuration file** link
4. Replace the contents with:

```python
import sys
import os

# Add your project directory to the path
path = '/home/yourusername/emerald-counselor-ai'
if path not in sys.path:
    sys.path.insert(0, path)

# Change to your project directory
os.chdir(path)

# Import your Flask app
from main import app as application

# Optional: Set up environment variables here if not using .env file
# import os
# os.environ['SECRET_KEY'] = 'your-secret-key'
# os.environ['OPENAI_API_KEY'] = 'your-api-key'
# os.environ['OPENAI_ASSISTANT_ID'] = 'your-assistant-id'
```

**Important:** Replace `yourusername` with your actual PythonAnywhere username!

## Step 8: Configure Web App

1. In the **Web** tab:
   - **Source code**: `/home/yourusername/emerald-counselor-ai`
   - **Working directory**: `/home/yourusername/emerald-counselor-ai`
   - **WSGI configuration file**: Should point to the file you just edited

2. **Static files mapping** (if needed):
   - URL: `/static/`
   - Directory: `/home/yourusername/emerald-counselor-ai/static/`

3. Click **Reload** to restart your web app

## Step 9: Test Your Application

1. Visit your PythonAnywhere URL (e.g., `yourusername.pythonanywhere.com`)
2. Test the login/signup functionality
3. Check that the database is working
4. Test the chat functionality

## Step 10: Set Up Scheduled Tasks (Optional)

If you need to run periodic tasks, you can use the **Tasks** tab to set up cron jobs.

## Troubleshooting

### Database Errors
- Make sure the database file has write permissions: `chmod 666 users.db`
- Check that the directory exists: `ls -la ~/emerald-counselor-ai/`

### Import Errors
- Check that all packages are installed: `pip3.10 list`
- Verify your Python version matches: `python3.10 --version`

### Environment Variables Not Loading
- Make sure `.env` file is in the project root
- Or set them in the Web tab's Environment variables section
- Or set them in the WSGI file

### Static Files Not Loading
- Verify static file mapping in Web tab
- Check file permissions: `chmod -R 755 static/`

### OpenAI API Errors
- Verify your API key is correct
- Check that you have API credits
- Verify the Assistant ID is correct

## Free Account Limitations

- Can only access your site at `yourusername.pythonanywhere.com` (no custom domains)
- External site visits are limited (your site sleeps after inactivity)
- Some restrictions on outbound connections
- PythonAnywhere wakes up your site when someone visits, but first visit after sleep may be slow

## Paid Account Benefits

- Custom domains
- Always-on (no sleeping)
- More outbound connections
- Better performance

## Notes

- Free accounts can only have one web app at a time
- Your database file (`users.db`) will persist in your home directory
- Make sure to back up your database regularly
- PythonAnywhere provides automatic backups for paid accounts

