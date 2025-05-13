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

# Check for the main frontend directory
if [ -d "frontend" ]; then
  echo "Frontend directory found, checking for package.json..."

  # First try the main frontend directory
  if [ -f "frontend/package.json" ]; then
    echo "Found package.json in main frontend directory"
    cd frontend
    echo "Changed to frontend directory: $(pwd)"
    echo "Installing dependencies..."
    npm install
    echo "Building frontend..."
    npm run build
    echo "Frontend build completed."
    cd ..
  # Then try the nested frontend directory
  elif [ -d "frontend/frontend" ] && [ -f "frontend/frontend/package.json" ]; then
    echo "Found package.json in nested frontend directory"
    cd frontend/frontend
    echo "Changed to nested frontend directory: $(pwd)"
    echo "Installing dependencies..."
    npm install
    echo "Building frontend..."
    npm run build
    echo "Frontend build completed."
    cd ../..
  # Try the root directory as a last resort
  elif [ -f "package.json" ]; then
    echo "Found package.json in root directory"
    echo "Installing dependencies..."
    npm install
    echo "Building frontend..."
    npm run build
    echo "Frontend build completed."
  else
    echo "ERROR: package.json not found in any expected location!"
    echo "Contents of frontend directory:"
    ls -la frontend
    echo "Contents of nested frontend directory (if exists):"
    if [ -d "frontend/frontend" ]; then
      ls -la frontend/frontend
    fi
    echo "Contents of root directory:"
    ls -la
    # Continue anyway, we'll create a fallback page later
    echo "Will continue with backend setup only."
  fi
else
  echo "ERROR: frontend directory not found!"
  echo "Contents of current directory:"
  ls -la
  # Continue anyway, we'll create a fallback page later
  echo "Will continue with backend setup only."
fi

# Step 2: Create necessary directories for Django
echo "Creating necessary directories for Django..."
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Step 3: Copy frontend build to Django static directory
echo "Copying frontend build to Django static directory..."

# Check all possible build locations
if [ -d "frontend/build" ] && [ "$(ls -A frontend/build 2>/dev/null)" ]; then
  echo "Frontend build directory found in main frontend directory, copying files..."
  cp -r frontend/build/* staticfiles/
  echo "Copy completed from frontend/build."
elif [ -d "frontend/frontend/build" ] && [ "$(ls -A frontend/frontend/build 2>/dev/null)" ]; then
  echo "Frontend build directory found in nested frontend directory, copying files..."
  cp -r frontend/frontend/build/* staticfiles/
  echo "Copy completed from frontend/frontend/build."
elif [ -d "build" ] && [ "$(ls -A build 2>/dev/null)" ]; then
  echo "Frontend build directory found in root directory, copying files..."
  cp -r build/* staticfiles/
  echo "Copy completed from build."
else
  echo "WARNING: Frontend build directory is missing or empty in all expected locations!"
  echo "Will continue with backend setup only."
  # Create a more detailed fallback page
  cat > staticfiles/index.html << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mengedmate - EV Charging Station Locator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: linear-gradient(135deg, #4a6cf7 0%, #2a3f9d 100%);
            color: white;
            text-align: center;
        }
        .container {
            max-width: 800px;
            padding: 20px;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 20px;
        }
        p {
            font-size: 1.2rem;
            margin-bottom: 30px;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background-color: white;
            color: #4a6cf7;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background-color: transparent;
            color: white;
            border: 2px solid white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Mengedmate</h1>
        <p>Find EV Charging Stations Anywhere, Anytime</p>
        <div>
            <a href="/api/auth/login/" class="btn">Login</a>
            <a href="/api/auth/register/" class="btn">Register</a>
        </div>
        <p style="margin-top: 30px; font-size: 0.9rem;">
            Note: Frontend build was not available during deployment.
            This is a fallback page.
        </p>
    </div>
</body>
</html>
EOL
  echo "Created fallback index.html in staticfiles directory."
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
