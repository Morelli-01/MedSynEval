# MedSynEval

Medical image evaluation system for assessing synthetic vs real medical images.

## Features

- **Invitation-based Registration**: Secure user registration with unique invitation tokens
- **Real-time Token Validation**: Modern Fetch API for seamless token verification
- **Dynamic Image Evaluation**: No page reloads, smooth image transitions
- **Map-like Image Viewer**: Intuitive pan and zoom controls
- **Profile Management**: Users can update their professional information
- **Admin Export**: Export all evaluations as JSON for analysis
- **MySQL Database**: Production-ready database backend

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup MySQL Database

**Option A: Using the setup script (recommended)**
```bash
./setup_mysql.sh
```

**Option B: Manual setup**
```bash
# Login to MySQL
mysql -u root -p

# Create database
CREATE DATABASE med_syn_eval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

See [MYSQL_SETUP.md](MYSQL_SETUP.md) for detailed instructions.

### 3. Configure Environment Variables

A `.env` file has been created with default values. **Update it with your MySQL password:**

```bash
# Edit .env file
nano .env
```

Update the `DATABASE_URL` line:
```env
DATABASE_URL=mysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/med_syn_eval
```

**Format:** `mysql://USERNAME:PASSWORD@HOST:PORT/DATABASE`

See [ENV_SETUP.md](ENV_SETUP.md) for detailed configuration options.

### 4. Run Migrations

```bash
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Create Invitation Tokens

```bash
python manage.py shell
>>> from evaluator.models import Invitation
>>> token = Invitation.objects.create()
>>> print(token.token)
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## Admin Features

### Exporting Evaluations

1. Login to admin at `/admin/`
2. Navigate to **Evaluations**
3. Select evaluations to export
4. Choose **"Export selected evaluations as JSON"** from Actions
5. Click **Go**

The exported JSON includes:
- Evaluation ID
- Clinician details (username, email, name, title, experience)
- Image path
- Classification (real/synthetic)
- Confidence level (1-5)
- Timestamp

## Project Structure

```
med_syn_eval/
├── evaluator/              # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── api_views.py       # API endpoints
│   ├── forms.py           # Form definitions
│   ├── admin.py           # Admin configuration
│   ├── templates/         # HTML templates
│   └── static/            # CSS, JS files
├── med_syn_eval/          # Project settings
├── data/                  # Image storage
│   ├── real/             # Real medical images
│   └── synth/            # Synthetic images
├── requirements.txt       # Python dependencies
├── setup_mysql.sh        # MySQL setup script
└── MYSQL_SETUP.md        # Detailed MySQL guide
```

## Technologies Used

- **Backend**: Django 5.0
- **Database**: MySQL 8.0+
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **APIs**: Modern Fetch API for async operations
- **Authentication**: Django built-in with custom user model

## Development

### Running Tests

```bash
python manage.py test evaluator
```

### Creating Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## License

[Your License Here]
