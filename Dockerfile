# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project
COPY . /app/

# Install frontend dependencies and build
RUN echo "Checking for frontend package.json in various locations..." && \
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then \
    echo "Found package.json in main frontend directory" && \
    cd frontend && npm install && npm run build && cd ..; \
    elif [ -d "frontend/frontend" ] && [ -f "frontend/frontend/package.json" ]; then \
    echo "Found package.json in nested frontend directory" && \
    cd frontend/frontend && npm install && npm run build && cd ../..; \
    elif [ -f "package.json" ]; then \
    echo "Found package.json in root directory" && \
    npm install && npm run build; \
    else \
    echo "Frontend package.json not found in any expected location"; \
    fi

# Create necessary directories
RUN mkdir -p static media staticfiles

# Copy frontend build to staticfiles if it exists (check all possible locations)
RUN echo "Checking for frontend build in various locations..." && \
    if [ -d "frontend/build" ] && [ "$(ls -A frontend/build 2>/dev/null)" ]; then \
    echo "Found build in main frontend directory" && \
    cp -r frontend/build/* staticfiles/ 2>/dev/null || echo "No files to copy"; \
    elif [ -d "frontend/frontend/build" ] && [ "$(ls -A frontend/frontend/build 2>/dev/null)" ]; then \
    echo "Found build in nested frontend directory" && \
    cp -r frontend/frontend/build/* staticfiles/ 2>/dev/null || echo "No files to copy"; \
    elif [ -d "build" ] && [ "$(ls -A build 2>/dev/null)" ]; then \
    echo "Found build in root directory" && \
    cp -r build/* staticfiles/ 2>/dev/null || echo "No files to copy"; \
    else \
    echo "Creating fallback index.html" && \
    echo '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Mengedmate</title><style>body{font-family:Arial;margin:0;padding:20px;background:linear-gradient(135deg,#4a6cf7 0%,#2a3f9d 100%);color:white;text-align:center;display:flex;justify-content:center;align-items:center;height:100vh;}h1{font-size:3rem;}a{color:white;}</style></head><body><div><h1>Mengedmate</h1><p>EV Charging Station Locator</p><p><a href="/api/auth/login/">Login</a> | <a href="/api/auth/register/">Register</a></p><p style="font-size:0.8rem">Note: Frontend build was not available during deployment.</p></div></body></html>' > staticfiles/index.html; \
    fi

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate --noinput

# Expose port
EXPOSE 8000

# Start Gunicorn
CMD ["gunicorn", "mengedmate.wsgi:application", "--bind", "0.0.0.0:8000"]
