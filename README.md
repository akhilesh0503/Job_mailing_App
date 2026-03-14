# 📧 Job Mailer — Setup Guide

A cold email automation tool that reads your Google Sheet, picks the right resume, generates personalized emails using Gemini AI, and sends them from your Gmail.

---

## 📁 Folder Structure

```
job-mailer/
├── app.py
├── requirements.txt
├── .env                      ← You create this (copy from .env.template)
├── service_account.json      ← You download this (see Step 3)
├── resume_software.pdf       ← Your software engineering resume
├── resume_datascience.pdf    ← Your data science resume
└── templates/
    └── index.html
```

---

## 🚀 Step-by-Step Setup

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

---

### Step 2 — Get a FREE Gemini API Key
1. Go to: https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Copy the key into your `.env` file as `GEMINI_API_KEY`

---

### Step 3 — Set up Google Sheets access (Service Account)

1. Go to: https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
5. Give it a name, click **Done**
6. Click the service account → **Keys tab → Add Key → JSON**
7. Download the JSON file → rename it to `service_account.json` → put it in the job-mailer folder
8. **Share your Google Sheet** with the service account's email (looks like `name@project.iam.gserviceaccount.com`) — give it **Viewer** access

---

### Step 4 — Set up Gmail App Password

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (if not already)
3. Search for **"App Passwords"** → Create one for "Mail"
4. Copy the 16-character password (with spaces is fine) into `.env`

> ⚠️ This is NOT your Gmail password. It's a special one-time password for apps.

---

### Step 5 — Prepare your Google Sheet

Your sheet should have columns like:

| Company | Job Link | Email | Recruiter Name |
|---------|----------|-------|----------------|
| Google  | https://careers.google.com/… | jane@google.com | Jane Doe |
| Netflix | https://jobs.netflix.com/…   | hr@netflix.com  | |

- **Recruiter Name** is optional — if blank, the tool extracts the first name from the email address

---

### Step 6 — Create your `.env` file

Copy `.env.template` to `.env` and fill in all values:
```bash
cp .env.template .env
```

---

### Step 7 — Add your resumes

Put your two PDF resumes in the job-mailer folder:
- `resume_software.pdf`
- `resume_datascience.pdf`

---

### Step 8 — Run the app!

```bash
python app.py
```

Then open your browser at: **http://localhost:5000**

---

## 🎯 How to Use

1. **Setup page** — Verify all green checkmarks ✅
2. **Google Sheet page** — Click "Load Sheet" to preview your data
3. **Compose & Preview** — Test a single email with live AI generation
4. **Bulk Send** — Select rows and fire all emails at once

---

## 🤖 How Resume Selection Works

The app reads the job description from the link and counts keywords:

- **Data Science keywords**: data science, machine learning, ML, analytics, SQL, Tableau, Python, AI, NLP, etc.
- **Software keywords**: software engineer, backend, frontend, React, Node, AWS, Docker, Kubernetes, etc.

Whichever score is higher → that resume gets attached.

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| "service_account.json not found" | Download JSON from Google Cloud Console, rename it |
| "GOOGLE_SHEET_ID not set" | Copy the ID from your sheet's URL |
| Gmail authentication error | Make sure App Password is correct and 2FA is on |
| Gemini rate limit | Free tier = 1500 requests/day, you're likely fine |
| Job description scraping fails | Some sites block scrapers; email will use basic template |
