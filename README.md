# CISADIM — Complaint Management System

A lightweight web application for managing client complaints in a calibration laboratory environment. Built and deployed as part of an internal quality management process (procedure FC 7.9-01).

**Live demo:** *(deployed on Render — link here once live)*

---

## What it does

Clients fill out a structured complaint form (in Spanish) covering:
- Contact information
- Details of the calibration service they received
- Nature and description of the complaint
- The corrective action they're requesting

Each submission gets a unique reference number (`QR-YYYY-XXXX`), is stored in a SQLite database, and is simultaneously synced to a private Google Sheet for real-time monitoring.

An internal admin panel (`/admin`) provides a clean two-panel interface to browse and review all received complaints.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask · Flask-CORS |
| Database | SQLite (local) + Google Sheets (cloud sync) |
| Auth | Google Service Account (via `google-auth`) |
| Frontend | Vanilla HTML/CSS/JS (single-file) |
| Deployment | Render (via `render.yaml`) |
| Process server | Gunicorn |

---

## Project structure

```
cisadim/
├── app.py              # Flask backend — routes, DB logic, Sheets sync
├── cisadim.html        # Frontend complaint form (served by Flask)
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
└── .gitignore
```

---

## Running locally

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/cisadim.git
cd cisadim
pip install -r requirements.txt

# 2. (Optional) Add Google Sheets credentials
#    Create a .env file or set the environment variable:
export GOOGLE_CREDENTIALS='{ ...your service account JSON... }'

# 3. Run
python app.py
```

The app will be available at `http://localhost:5000`.  
Admin panel at `http://localhost:5000/admin`.

> **Note:** The app works fully without Google credentials — complaints are saved to SQLite only. Google Sheets sync is optional and fails gracefully.

---

## Deploying to Render

1. Push this repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com) and connect the repo.
3. Render will auto-detect `render.yaml` and configure the build.
4. Add your `GOOGLE_CREDENTIALS` environment variable in the Render dashboard (paste the full service account JSON as a single-line string).

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_CREDENTIALS` | No | Full JSON of your Google service account, for Sheets sync |

---

## Author

**José Ignacio Soto Bastías** — Mining Engineer · Data Scientist  
[LinkedIn](www.linkedin.com/in/jose-soto-bastias) · [GitHub](https://github.com/YOUR_USERNAME)
