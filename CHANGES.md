# Database Migration & Admin Export - Summary

## Changes Made

### 1. Database Migration to MySQL

#### Files Modified:
- **`med_syn_eval/settings.py`**
  - Changed database engine from SQLite to MySQL
  - Configuration:
    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'med_syn_eval',
            'USER': 'root',
            'PASSWORD': '',  # UPDATE THIS
            'HOST': 'localhost',
            'PORT': '3306',
        }
    }
    ```

#### Files Created:
- **`requirements.txt`** - Added mysqlclient dependency
- **`MYSQL_SETUP.md`** - Comprehensive MySQL setup guide
- **`setup_mysql.sh`** - Automated database setup script
- **`README.md`** - Updated project documentation

### 2. Admin Export Functionality

#### Files Modified:
- **`evaluator/admin.py`**
  - Added `EvaluationAdmin` class with export functionality
  - New admin action: "Export selected evaluations as JSON"
  - Features:
    - Select multiple evaluations in admin
    - Export as formatted JSON file
    - Includes all evaluation data + clinician info
    - Timestamped filename

#### Export JSON Structure:
```json
[
  {
    "id": 1,
    "clinician": {
      "username": "doctor1",
      "email": "doctor@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "title": "Dr.",
      "years_experience": 10
    },
    "image_path": "real/image001.jpg",
    "is_real": true,
    "confidence": 5,
    "timestamp": "2025-12-10T10:30:00"
  }
]
```

## Setup Instructions

### Quick Setup (3 steps):

1. **Install MySQL Client**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**
   ```bash
   ./setup_mysql.sh
   ```
   Or manually create database:
   ```sql
   CREATE DATABASE med_syn_eval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **Update Password in settings.py**
   Edit `med_syn_eval/settings.py` line 79:
   ```python
   'PASSWORD': 'your_mysql_password',
   ```

4. **Run Migrations**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Using the Export Feature

### Step-by-Step:

1. **Access Admin Panel**
   - Navigate to `http://localhost:8000/admin/`
   - Login with superuser credentials

2. **Go to Evaluations**
   - Click on "Evaluations" in the admin menu

3. **Select Evaluations**
   - Check the boxes next to evaluations you want to export
   - Or use "Select all" to export everything

4. **Export**
   - From the "Action" dropdown, select "Export selected evaluations as JSON"
   - Click "Go"
   - A JSON file will download automatically

5. **File Name Format**
   - `evaluations_export_YYYYMMDD_HHMMSS.json`
   - Example: `evaluations_export_20251210_103045.json`

## Benefits

### MySQL Advantages:
- ✅ Production-ready database
- ✅ Better performance for large datasets
- ✅ ACID compliance
- ✅ Concurrent access support
- ✅ Better backup/restore options
- ✅ Industry standard

### Export Feature Benefits:
- ✅ Easy data analysis
- ✅ Backup evaluations
- ✅ Share data with researchers
- ✅ Import into analysis tools (Python, R, Excel)
- ✅ Timestamped exports for versioning
- ✅ Includes all relevant metadata

## Troubleshooting

### MySQL Connection Issues:
```bash
# Check if MySQL is running
sudo systemctl status mysql

# Start MySQL
sudo systemctl start mysql

# Test connection
mysql -u root -p
```

### Migration Issues:
```bash
# If you get errors, try:
python manage.py migrate --run-syncdb

# Or reset database (WARNING: deletes all data)
mysql -u root -p
DROP DATABASE med_syn_eval;
CREATE DATABASE med_syn_eval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
python manage.py migrate
```

### mysqlclient Installation Issues:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential

# Then retry
pip install mysqlclient
```

## Testing

The existing tests still work with MySQL:
```bash
python manage.py test evaluator
```

Note: Tests use a separate test database automatically.

## Rollback to SQLite (if needed)

If you need to switch back to SQLite:

1. Edit `settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': BASE_DIR / 'db.sqlite3',
       }
   }
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

## Next Steps

1. ✅ Update MySQL password in settings.py
2. ✅ Run `./setup_mysql.sh` or create database manually
3. ✅ Run `python manage.py migrate`
4. ✅ Create superuser: `python manage.py createsuperuser`
5. ✅ Test the application
6. ✅ Try the export feature in admin

---

**All changes are backward compatible with existing code!**
