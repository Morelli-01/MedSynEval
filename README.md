# MedSynEval

A Django-based web application for evaluating synthetic vs real medical images through clinician assessments.

## Features

- Invitation-based secure registration
- Real-time image evaluation with pan/zoom viewer
- Profile management for clinicians
- Admin export of evaluations as JSON
- MySQL database backend

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Create MySQL database
mysql -u root -p -e "CREATE DATABASE med_syn_eval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. Configure Environment
Update `.env` with your MySQL credentials:
```env
DATABASE_URL=mysql://root:YOUR_PASSWORD@localhost:3306/med_syn_eval
```

### 4. Initialize Application
```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Create invitation token
python manage.py shell -c "from evaluator.models import Invitation; token = Invitation.objects.create(); print(f'Token: {token.token}')"

# Start server
python manage.py runserver
```

Visit `http://localhost:8000`

## Project Structure

```
med_syn_eval/
├── evaluator/          # Main app (models, views, templates)
├── med_syn_eval/       # Project settings
├── data/               # Image storage (real/ and synth/)
└── static/             # Static files (favicon, etc.)
```

## Tech Stack

- Django 5.0
- MySQL 8.0+
- Bootstrap 5
- Vanilla JavaScript

## License

[Your License Here]
