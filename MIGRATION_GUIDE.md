# Database Migration Guide

## Overview

This project uses individual databases for each developer to avoid conflicts. Therefore, **migration files are NOT committed to git** to prevent merge conflicts and schema inconsistencies.

Each developer manages their own migrations locally.

---

## ✅ What's Ignored

The following are ignored in `.gitignore`:
```
alembic/versions/*.py          # Migration files
alembic/versions/__pycache__/  # Migration cache
*.db                           # SQLite databases
*.sqlite                       # SQLite databases
*.sqlite3                      # SQLite databases
migrations/versions/*.py       # Alternative migrations folder
```

---

## 📋 How to Handle Migrations Locally

### Option 1: Automatic Database Creation (RECOMMENDED)

The databases are created automatically when you run the application:

```python
# In main.py
Base.metadata.create_all(bind=engine)
```

This creates all tables without needing manual migrations.

### Option 2: Manual Alembic Migrations (If Using)

If you need to create migrations locally:

```bash
# Create a new migration file
alembic revision --autogenerate -m "Your migration message"

# Apply the migration
alembic upgrade head
```

**These files stay local on your machine and are NOT pushed to git.**

---

## 🚀 Setting Up a New Development Environment

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd mtm-platform-backend
```

### Step 2: Create Virtual Environment
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure .env
Create your local `.env` file with your database credentials:
```
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=your_local_db
```

### Step 5: Run Seed Script (First Time Only)
```bash
python seed.py
```

This initializes your local database with:
- Default roles
- Sample users
- Permissions

### Step 6: Start the Server
```bash
python main.py
```

---

## 🔄 Workflow for Your Team

### When pulling new code:

1. **Get latest code from git**
   ```bash
   git pull origin main
   ```

2. **Install any new dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Your local migrations remain untouched** ✅
   - Each developer's migrations stay local
   - No conflicts from different branches
   - Each database evolves independently

### When pushing code:

```bash
git add .
git commit -m "Your changes (migrations excluded)"
git push origin main
```

Migration files are automatically excluded ✅

---

## ⚠️ Important Notes

### DO NOT Commit Migrations
If you see migration files in your git staging:
```bash
# Don't commit them!
git rm --cached alembic/versions/*.py
```

### Handle Model Changes
If you modify models and want to apply changes:

**Option A: Just add columns (easiest)**
- Run `python seed.py` again first time
- For new tables, the application will create them

**Option B: Use manual migrations**
```bash
alembic revision --autogenerate -m "Add new column to users"
alembic upgrade head
```

**Option C: Delete and recreate database**
```bash
# Drop your local database
# Re-run seed.py to create fresh database
python seed.py
```

---

## 🆘 Troubleshooting

### "Table already exists" error?
```bash
# Option 1: Drop your local database and recreate
mysql -u root -p
DROP DATABASE mtm_db;
quit

# Run seed script again
python seed.py
```

### Different database schema across team?
- This is expected! Each developer has their own database
- Always run `python seed.py` when setting up
- Latest model changes are in the Python code

### Need to share schema changes?
- Modify the model in `app/modules/auth/models.py`
- Commit the model changes to git
- Team members will use updated models with their local databases

---

## 📚 Related Files

- **Models**: `app/modules/auth/models.py`
- **Alembic Config**: `alembic.ini`, `alembic/env.py`
- **Main App**: `main.py` (creates tables automatically)
- **Seed Script**: `seed.py` (initializes data)

---

## ✅ Verification

To verify migrations are properly ignored:

```bash
# This should show NOTHING related to migrations
git status

# These files should appear as ignored:
git status --ignored | grep alembic
```

---

## 💡 Best Practices

1. ✅ Always run `python seed.py` when setting up
2. ✅ Keep your local `.env` file different
3. ✅ Commit only model changes, not migrations
4. ✅ Sync model changes with team via git
5. ✅ Each developer applies migrations locally as needed

---

## Questions?

If you have issues:
1. Check your `.env` database credentials
2. Verify MySQL is running
3. Run `python seed.py` to reinitialize
4. Check `.gitignore` is properly set
5. See troubleshooting section above

---

**Last Updated**: February 16, 2026
**Status**: Team-Ready ✅
