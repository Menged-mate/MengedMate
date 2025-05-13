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
RUN if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then \
    cd frontend && npm install && npm run build && cd ..; \
    else \
    echo "Frontend directory or package.json not found"; \
    fi

# Create necessary directories
RUN mkdir -p static media staticfiles

# Copy frontend build to staticfiles if it exists
RUN if [ -d "frontend/build" ]; then \
    cp -r frontend/build/* staticfiles/ 2>/dev/null || echo "No files to copy"; \
    else \
    echo "<html><body><h1>Mengedmate</h1><p>Frontend build not available.</p></body></html>" > staticfiles/index.html; \
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
