#!/usr/bin/env bash
# Exit on error, undefined, and pipe failures
set -o errexit

echo "========================================="
echo "PaperAIzer Build Script for Render"
echo "========================================="
echo "DATABASE_URL: ${DATABASE_URL:0:20}..."
echo ""

echo "=== Step 1: Installing Python dependencies ==="
if pip install -r requirements.txt; then
    echo "✓ Dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

echo ""
echo "=== Step 2: Collecting static files ==="
if python manage.py collectstatic --no-input --clear 2>&1; then
    echo "✓ Static files collected"
else
    echo "⚠ Static file collection had issues (continuing...)"
fi

echo ""
echo "=== Step 3: Running database migrations ==="
if python manage.py migrate --no-input 2>&1; then
    echo "✓ Database migrations completed"
else
    echo "✗ migrations FAILED - DATABASE CONNECTION ISSUE"
    exit 1
fi

echo ""
echo "=== Step 4: Creating superuser (if needed) ==="
python manage.py shell << 'EOF' 2>&1 || echo "⚠ Superuser creation had issues"
try:
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@paperaizer.com', 'admin123')
        print("✓ Superuser 'admin' created")
    else:
        print("✓ Superuser 'admin' already exists")
except Exception as e:
    print(f"⚠ Superuser creation error: {e}")
EOF

echo ""
echo "========================================="
echo "✓ Build script completed!"
echo "========================================="
