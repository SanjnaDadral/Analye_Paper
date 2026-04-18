#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "========================================="
echo "PaperAIzer Build Script for Render"
echo "========================================="

echo ""
echo "=== Step 1: Installing Python dependencies ==="
pip install -r requirements.txt
echo "✓ Dependencies installed"

echo ""
echo "=== Step 2: Running database migrations ==="
python manage.py migrate --no-input
echo "✓ Migrations applied"

echo ""
echo "=== Step 3: Collecting static files ==="
python manage.py collectstatic --no-input --clear
echo "✓ Static files collected"

echo ""
echo "=== Step 4: Downloading NLTK data ==="
python -c "
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)
print('NLTK data downloaded')
"
echo "✓ NLTK data ready"

echo ""
echo "========================================="
echo "✓ Build complete!"
echo "========================================="
