import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq
import requests
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

GROQ_API_KEY         = os.getenv("GROQ_API_KEY", "")
GMAIL_ADDRESS        = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "")
GOOGLE_SHEET_ID      = os.getenv("GOOGLE_SHEET_ID", "")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON", "")
TEMPLATES_FILE       = os.getenv("TEMPLATES_FILE", "templates.json")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ── Role groups for LLM template matching ────────────────────────────────────
TEMPLATE_ROLE_GROUPS = {
    "software_engineer": [
        "Software Engineer", "Software Engineer I", "Software Engineer Entry Level",
        "Junior Software Engineer", "Associate Software Engineer", "Graduate Software Engineer",
        "Early Career Software Engineer", "New Grad Software Engineer", "Software Developer I",
        "Application Software Engineer", "SDE", "SWE"
    ],
    "backend_engineer": [
        "Backend Software Engineer", "Backend Engineer", "Backend Engineer I",
        "Backend Platform Engineer", "API Engineer", "Server Side Software Engineer",
        "Platform Software Engineer", "Systems Backend Engineer"
    ],
    "data_engineer": [
        "Data Engineer", "Junior Data Engineer", "Associate Data Engineer",
        "Data Platform Engineer", "Data Infrastructure Engineer", "Analytics Engineer",
        "ETL Engineer", "Data Pipeline Engineer"
    ],
    "ai_ml_engineer": [
        "ML Engineer", "Machine Learning Engineer", "AI Engineer",
        "AI Infrastructure Engineer", "ML Platform Engineer", "LLM Engineer",
        "Applied AI Engineer", "AI Systems Engineer", "NLP Engineer"
    ],
    "infrastructure_engineer": [
        "Infrastructure Software Engineer", "Distributed Systems Engineer",
        "Systems Software Engineer", "Cloud Infrastructure Engineer",
        "Platform Infrastructure Engineer", "Cloud Software Engineer",
        "Cloud Platform Engineer", "Cloud Applications Engineer", "DevOps Engineer", "SRE"
    ],
    "fullstack_engineer": [
        "Full Stack Engineer", "Software Engineer Full Stack", "Product Engineer",
        "Full Stack Developer", "Frontend Engineer", "React Engineer"
    ],
    "data_analyst": [
        "Data Analyst", "Data Analyst Engineer", "Analytics Platform Engineer",
        "Applied Data Engineer", "Business Analyst", "BI Engineer"
    ],
    "data_scientist": [
        "Data Scientist", "Research Scientist", "Applied Scientist",
        "ML Researcher", "Data Science Engineer"
    ],
    "startup_engineer": [
        "Founding Engineer", "Founding Software Engineer", "Early Engineer",
        "Generalist Engineer", "Staff Engineer"
    ],
    "general": ["General", "Other"]
}

DEFAULT_TEMPLATES = {
    "software_engineer": {
        "display_name": "Software Engineer",
        "group": "Core Software",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} role at {company_name} and was really excited by the work your team is doing.\n\nI have experience building scalable backend systems and full-stack applications, and I believe I'd be a strong fit. I've attached my resume for your review — would love to connect if there's an opportunity.\n\nBest regards,\n{sender_name}"
    },
    "backend_engineer": {
        "display_name": "Backend Engineer",
        "group": "Core Software",
        "body": "Hi {recruiter_name},\n\nI noticed the {job_role} opening at {company_name} and wanted to reach out directly.\n\nI have strong experience in Python, REST APIs, and distributed systems, and I'm confident I could contribute meaningfully to your backend team. I've attached my resume — would love to connect.\n\nBest regards,\n{sender_name}"
    },
    "data_engineer": {
        "display_name": "Data Engineer",
        "group": "Data",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} position at {company_name} and it immediately caught my attention.\n\nI have hands-on experience building ETL pipelines, working with Spark and SQL, and managing data infrastructure on AWS. I've attached my resume and would love the chance to connect.\n\nBest regards,\n{sender_name}"
    },
    "ai_ml_engineer": {
        "display_name": "AI / ML Engineer",
        "group": "AI & ML",
        "body": "Hi {recruiter_name},\n\nI saw the {job_role} role at {company_name} and was genuinely excited — this aligns directly with the work I've been doing.\n\nI have experience building LLM pipelines, fine-tuning models, and deploying ML systems at scale. I've attached my resume and would love to explore if there's a fit.\n\nBest regards,\n{sender_name}"
    },
    "infrastructure_engineer": {
        "display_name": "Infrastructure / Cloud Engineer",
        "group": "Infrastructure",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} opportunity at {company_name} and wanted to reach out.\n\nI have experience with AWS (Lambda, S3, SQS), distributed systems, and event-driven architectures. I believe my background would be a strong fit for your infrastructure team. Resume attached!\n\nBest regards,\n{sender_name}"
    },
    "fullstack_engineer": {
        "display_name": "Full Stack Engineer",
        "group": "Core Software",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} role at {company_name} and I'm very interested in joining your team.\n\nI have experience across frontend (React) and backend (Node, Python, REST APIs), and enjoy building end-to-end features. I've attached my resume for your review.\n\nBest regards,\n{sender_name}"
    },
    "data_analyst": {
        "display_name": "Data Analyst",
        "group": "Data",
        "body": "Hi {recruiter_name},\n\nI noticed the {job_role} opening at {company_name} and wanted to reach out directly.\n\nI have strong experience in data analysis, SQL, and visualization tools like Tableau and Power BI. I'm excited about the chance to contribute to your analytics team. Resume attached!\n\nBest regards,\n{sender_name}"
    },
    "data_scientist": {
        "display_name": "Data Scientist",
        "group": "Data",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} position at {company_name} and was really excited by the work your team is doing.\n\nI have hands-on experience in machine learning, statistical modeling, and translating data into actionable insights. I've attached my resume and would love the chance to chat.\n\nBest regards,\n{sender_name}"
    },
    "startup_engineer": {
        "display_name": "Startup / Founding Engineer",
        "group": "Startup",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} role at {company_name} and I'm really excited about what you're building.\n\nI thrive in fast-moving environments and love owning things end to end. I'm a strong generalist with experience across backend, data, and infrastructure — and I'd love to bring that energy to your team. Resume attached!\n\nBest regards,\n{sender_name}"
    },
    "general": {
        "display_name": "General",
        "group": "Other",
        "body": "Hi {recruiter_name},\n\nI came across the {job_role} role at {company_name} and wanted to reach out directly.\n\nI'm very interested in contributing to your team and believe my background would be a strong fit. I've attached my resume for your consideration — I'd love to connect.\n\nBest regards,\n{sender_name}"
    }
}


def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        try:
            with open(TEMPLATES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    save_templates(DEFAULT_TEMPLATES)
    return DEFAULT_TEMPLATES


def save_templates(templates):
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(templates, f, indent=2)


def get_sheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def get_sheet_data():
    try:
        sheet = get_sheet_client()
        records = sheet.get_all_records()
        return records, sheet, None
    except Exception as e:
        return [], None, str(e)


def flag_row_in_sheet(company_name, job_role, user_num):
    flag_col_name = f"Flag_{user_num}"
    try:
        sheet = get_sheet_client()
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        if flag_col_name not in headers:
            return False, f"{flag_col_name} column not found"
        flag_col = headers.index(flag_col_name) + 1
        for i, row in enumerate(records, start=2):
            if (row.get("Company_Name", "").strip().lower() == company_name.strip().lower() and
                    row.get("Job_Role", "").strip().lower() == job_role.strip().lower()):
                sheet.update_cell(i, flag_col, "SENT")
                return True, "Flagged"
        return False, "Row not found"
    except Exception as e:
        return False, str(e)


def parse_mail_entries(raw):
    entries = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if " - " in part:
            email_part, name_part = part.split(" - ", 1)
            entries.append({"email": email_part.strip(), "name": name_part.strip().capitalize()})
        else:
            entries.append({"email": part, "name": None})
    return entries


def select_template(job_role):
    templates = load_templates()

    if groq_client:
        prompt = f"""You are an expert technical recruiter who deeply understands software engineering job titles.

A candidate has applied for this role: "{job_role}"

Pick the single best matching template key from the list below.

Template keys and what they cover:
- software_engineer: Any general software engineering role. Software Engineer, Software Development Engineer, SDE, SWE, New Grad Engineer, Associate Engineer, Graduate Engineer, Early Career Engineer, Application Engineer, Software Developer.
- backend_engineer: Backend Engineer, Backend Developer, API Engineer, Platform Engineer, Server Side Engineer, Systems Engineer.
- fullstack_engineer: Full Stack Engineer, Full Stack Developer, Product Engineer, Frontend Engineer, React Engineer.
- data_engineer: Data Engineer, ETL Engineer, Analytics Engineer, Data Platform Engineer, Data Infrastructure Engineer, Data Pipeline Engineer.
- data_analyst: Data Analyst, Business Analyst, BI Analyst, Reporting Analyst, Insights Analyst.
- data_scientist: Data Scientist, Research Scientist, Applied Scientist, ML Researcher.
- ai_ml_engineer: ML Engineer, Machine Learning Engineer, AI Engineer, LLM Engineer, NLP Engineer, Applied AI Engineer, AI Infrastructure Engineer.
- infrastructure_engineer: Infrastructure Engineer, Cloud Engineer, DevOps Engineer, SRE, Platform Infrastructure Engineer, Distributed Systems Engineer.
- startup_engineer: Founding Engineer, Early Engineer, Generalist Engineer, Startup Engineer.
- general: Use ONLY if nothing else fits at all.

Return ONLY the key. No explanation. No punctuation. Just the key exactly as written above."""

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            raw = response.choices[0].message.content
            print(f"[DEBUG] Groq raw response: {repr(raw)}")
            key = raw.strip().lower().replace(" ", "_").replace("-", "_").strip('"').strip("'").strip()
            print(f"[DEBUG] Cleaned key: {repr(key)}")
            return key if key in templates else "general"
        except Exception as e:
            print(f"[DEBUG] Groq exception: {e}")

    return "general"


def build_email_body(template_key, recruiter_name, company_name, sender_name, job_role=""):
    templates = load_templates()
    tmpl = templates.get(template_key, templates.get("general", DEFAULT_TEMPLATES["general"]))
    body = tmpl["body"]
    return body.format(
        recruiter_name=recruiter_name if recruiter_name else "there",
        company_name=company_name,
        sender_name=sender_name,
        job_role=job_role
    )


def send_email(to_address, subject, body, resume_path, sender_name):
    try:
        msg = MIMEMultipart()
        msg["From"]    = f"{sender_name} <{GMAIL_ADDRESS}>"
        msg["To"]      = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        if resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(resume_path)}")
            msg.attach(part)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())
        return True, "Sent!"
    except Exception as e:
        return False, str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config-status")
def config_status():
    issues = []
    if not GROQ_API_KEY:       issues.append("GROQ_API_KEY not set")
    if not GMAIL_ADDRESS:      issues.append("GMAIL_ADDRESS not set")
    if not GMAIL_APP_PASSWORD: issues.append("GMAIL_APP_PASSWORD not set")
    if not GOOGLE_SHEET_ID:    issues.append("GOOGLE_SHEET_ID not set")
    if not SERVICE_ACCOUNT_JSON:
        issues.append("SERVICE_ACCOUNT_JSON not set")
    return jsonify({"ok": len(issues) == 0, "issues": issues,
                    "gmail": GMAIL_ADDRESS, "groq": bool(GROQ_API_KEY)})


@app.route("/api/load-sheet")
def load_sheet():
    user_num = request.args.get("user", "1")
    mail_col = f"Mail_IDs_{user_num}"
    flag_col = f"Flag_{user_num}"
    records, _, error = get_sheet_data()
    if error:
        return jsonify({"ok": False, "error": error})
    companies = {}
    for row in records:
        company  = str(row.get("Company_Name", "")).strip()
        job_role = str(row.get("Job_Role", "")).strip()
        job_link = str(row.get("Job_Link", "")).strip()
        mail_ids = str(row.get(mail_col, "")).strip()
        flag     = str(row.get(flag_col, "")).strip().upper()
        if not company or not job_role:
            continue
        if company not in companies:
            companies[company] = []
        companies[company].append({
            "job_role":     job_role,
            "job_link":     job_link,
            "mail_entries": parse_mail_entries(mail_ids),
            "flagged":      flag == "SENT"
        })
    return jsonify({"ok": True, "companies": companies})


@app.route("/api/preview-emails", methods=["POST"])
def preview_emails():
    data         = request.json
    company      = data.get("company", "")
    job_role     = data.get("job_role", "")
    mail_entries = data.get("mail_entries", [])
    sender_name  = data.get("sender_name", "")
    template_key  = select_template(job_role)
    templates     = load_templates()
    template_name = templates.get(template_key, {}).get("display_name", template_key)
    subject       = f"Interested in {job_role} Opportunities at {company}"
    previews = []
    for entry in mail_entries:
        email      = entry.get("email", "")
        first_name = entry.get("name")
        body = build_email_body(template_key, first_name, company, sender_name, job_role)
        previews.append({
            "email":          email,
            "recruiter_name": first_name or "there",
            "subject":        subject,
            "body":           body,
            "template_used":  template_name
        })
    return jsonify({"ok": True, "template_key": template_key,
                    "template_name": template_name, "previews": previews})


@app.route("/api/send-emails", methods=["POST"])
def send_emails():
    data        = request.json
    company     = data.get("company", "")
    job_role    = data.get("job_role", "")
    emails_data = data.get("emails", [])
    sender_name = data.get("sender_name", "")
    resume_path = data.get("resume_path", "")
    user_num    = data.get("user_num", "1")
    results  = []
    all_sent = True
    for item in emails_data:
        success, msg = send_email(item.get("email"), item.get("subject"),
                                  item.get("body"), resume_path, sender_name)
        results.append({"email": item.get("email"), "ok": success, "message": msg})
        if not success:
            all_sent = False
    flag_msg = ""
    if all_sent and company and job_role:
        _, flag_msg = flag_row_in_sheet(company, job_role, user_num)
    return jsonify({"ok": True, "results": results, "flagged": all_sent, "flag_message": flag_msg})


@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"})
    file = request.files["resume"]
    if not file.filename:
        return jsonify({"ok": False, "error": "Empty filename"})
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, file.filename)
    file.save(save_path)
    return jsonify({"ok": True, "path": save_path, "filename": file.filename})


@app.route("/api/templates", methods=["GET"])
def get_templates():
    return jsonify({"ok": True, "templates": load_templates()})


@app.route("/api/templates", methods=["POST"])
def save_templates_route():
    data = request.json
    templates = data.get("templates", {})
    if not templates:
        return jsonify({"ok": False, "error": "No templates provided"})
    try:
        save_templates(templates)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/templates/<key>", methods=["DELETE"])
def delete_template(key):
    templates = load_templates()
    if key == "general":
        return jsonify({"ok": False, "error": "Cannot delete the general template"})
    if key in templates:
        del templates[key]
        save_templates(templates)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Template not found"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
