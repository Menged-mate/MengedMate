#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting combined build process..."

# Step 1: Build the frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Step 2: Create necessary directories for Django
echo "Creating necessary directories for Django..."
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Step 3: Copy frontend build to Django static directory
echo "Copying frontend build to Django static directory..."
cp -r frontend/build/* staticfiles/

# Step 4: Install backend dependencies
echo "Installing backend dependencies..."
pip install -r requirements.txt

# Step 5: Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Step 6: Check for Django errors
echo "Checking for Django errors..."
python manage.py check

# Step 7: Apply migrations
echo "Applying migrations..."
python manage.py migrate --noinput --run-syncdb

# Step 8: Create a simple index.html file in templates directory if it doesn't exist
echo "Ensuring templates directory exists..."
mkdir -p templates

echo "Creating index.html if it doesn't exist..."
if [ ! -f "templates/index.html" ]; then
  echo "Creating simple index.html..."
  cat > templates/index.html << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="0;url=/static/index.html">
    <title>Mengedmate - Redirecting...</title>
</head>
<body>
    <p>Redirecting to the application...</p>
    <script>
        window.location.href = "/static/index.html";
    </script>
</body>
</html>
EOL
fi

echo "Build completed successfully!"
