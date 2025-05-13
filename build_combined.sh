#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting combined build process..."

# Print current directory for debugging
echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la

# Step 1: Build the frontend
echo "Building frontend..."
if [ -d "frontend" ]; then
  cd frontend
  echo "Changed to frontend directory: $(pwd)"
  echo "Checking for package.json:"
  ls -la

  if [ -f "package.json" ]; then
    echo "Found package.json, installing dependencies..."
    npm install
    echo "Building frontend..."
    npm run build
    echo "Frontend build completed."
  else
    echo "ERROR: package.json not found in frontend directory!"
    echo "Contents of frontend directory:"
    ls -la
    exit 1
  fi

  cd ..
else
  echo "ERROR: frontend directory not found!"
  exit 1
fi

# Step 2: Create necessary directories for Django
echo "Creating necessary directories for Django..."
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Step 3: Copy frontend build to Django static directory
echo "Copying frontend build to Django static directory..."
if [ -d "frontend/build" ] && [ "$(ls -A frontend/build 2>/dev/null)" ]; then
  echo "Frontend build directory exists and is not empty, copying files..."
  cp -r frontend/build/* staticfiles/
  echo "Copy completed."
else
  echo "WARNING: Frontend build directory is missing or empty!"
  echo "Will continue with backend setup only."
  # Create a simple index.html in staticfiles as a fallback
  echo "<html><body><h1>Mengedmate</h1><p>Frontend build not available.</p></body></html>" > staticfiles/index.html
fi

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
