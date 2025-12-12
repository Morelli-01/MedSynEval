# MedSynEval

A Django-based web application for evaluating synthetic vs real medical images through clinician assessments.

## Features

- **ImageSet Management**: Load and organize groups of images for evaluation
- **Assignment System**: Assign specific image sets to clinicians
- **Dynamic Evaluation**: Seamless evaluation using Fetch API (no page reloads)
- **Progress Tracking**: Monitor evaluation progress in real-time
- **Invitation-based Registration**: Secure clinician registration
- **Interactive Image Viewer**: Pan/zoom viewer for detailed inspection
- **Admin Analytics**: Export evaluations and view comprehensive statistics
- **MySQL Database**: Robust data storage

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

## Loading Images

### Quick Example

Prepare your data folder:
```
data_folder/
├── real/
│   ├── image1.jpg
│   └── ...
└── synth/
    ├── image1.jpg
    └── ...
```

Load images:
```bash
python manage.py load_imageset /path/to/data_folder "Study Name"
```

Then create assignments via admin panel at `http://localhost:8000/admin/`

## Complete Documentation

📖 **See [DOCUMENTATION.md](DOCUMENTATION.md) for complete guide including:**
- Detailed loading instructions
- Admin workflow
- Clinician workflow
- Dynamic evaluation system
- API reference
- Troubleshooting
- Best practices

## Tech Stack

- Django 5.0
- MySQL 8.0+
- Bootstrap 5
- Vanilla JavaScript with Fetch API
- Pillow (image handling)

