# Mengedmate - EV Charging Station Locator

A web application to locate EV charging stations with email verification authentication and station owner management.

## Features

### For Regular Users

- User authentication with email verification
- Mobile-responsive design
- Profile management with EV battery capacity and connector type
- EV charging station locator (coming soon)

### For Station Owners

- Station owner registration with verification process
- Station management dashboard
- Profile and business information management
- Verification badge for trusted station owners

## Tech Stack

### Backend

- Django
- Django Rest Framework (DRF)
- Django Allauth for authentication
- PostgreSQL (production), SQLite (development)
- Whitenoise for static files
- Gunicorn for production server

### Frontend

- React
- React Router
- Axios for API requests
- Modern responsive UI

## Setup Instructions

### Backend Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd mengedmate
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run migrations:

```bash
python manage.py migrate
```

5. Create a superuser:

```bash
python manage.py createsuperuser
```

6. Start the Django development server:

```bash
python manage.py runserver
```

The backend server will be running at http://localhost:8000/

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the React development server:

```bash
npm start
```

The frontend will be running at http://localhost:3000/

## API Endpoints

### Authentication

- `POST /api/auth/register/` - Register a new user
- `POST /api/auth/verify-email/` - Verify email with code
- `POST /api/auth/login/` - Login user
- `POST /api/auth/logout/` - Logout user
- `POST /api/auth/resend-verification/` - Resend verification code
- `GET/PUT /api/auth/profile/` - Get or update user profile

## Development

### Backend Development

To add new features to the backend:

1. Create a new Django app:

```bash
python manage.py startapp app_name
```

2. Add the app to `INSTALLED_APPS` in `settings.py`
3. Create models, serializers, views, and URLs
4. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Frontend Development

To add new features to the frontend:

1. Create new components in the `frontend/src/components` directory
2. Add routes in `App.js`
3. Create services for API calls in `frontend/src/services` directory

## Deployment

This application consists of a Django backend and a React frontend that need to be deployed separately.

### Prerequisites

1. A web hosting service for the Django backend (e.g., Heroku, DigitalOcean, AWS)
2. A static site hosting service for the React frontend (e.g., Netlify, Vercel, AWS S3)
3. A PostgreSQL database service

### Backend Deployment

1. Set up a PostgreSQL database
2. Configure the environment variables:
   - `SECRET_KEY`: A secure random string
   - `DEBUG`: Set to 'False' for production
   - `ALLOWED_HOSTS`: Add your domain names
   - `DATABASE_URL`: PostgreSQL connection string
   - `CORS_ALLOWED_ORIGINS`: Your frontend URL
   - `FRONTEND_URL`: URL of the frontend application
   - `EMAIL_HOST_USER`: Gmail address for sending emails
   - `EMAIL_HOST_PASSWORD`: Gmail app password
3. Run the build script: `./build.sh`
4. Start the Django application with Gunicorn: `gunicorn mengedmate.wsgi:application`

### Frontend Deployment

1. Set the backend API URL in `.env.production`:
   ```
   REACT_APP_API_URL=https://your-backend-domain.com
   ```
2. Build the React application:
   ```
   cd frontend
   npm install
   npm run build
   ```
3. Deploy the contents of the `frontend/build` directory to your static site hosting service

### Separate vs. Combined Deployment

You can deploy the frontend and backend separately (recommended) or together:

#### Separate Deployment (Recommended)

- Deploy the Django backend to a web server
- Deploy the React frontend to a static site host
- Configure CORS settings to allow communication between the two

#### Combined Deployment

- Serve the React frontend as static files from Django
- Configure Django to serve the React app for non-API routes
- This approach requires additional configuration not included in this repository

## Environment Variables

### Backend

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to 'True' for development, 'False' for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: PostgreSQL connection string (production only)
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS
- `FRONTEND_URL`: URL of the frontend application
- `EMAIL_HOST_USER`: Gmail address for sending emails
- `EMAIL_HOST_PASSWORD`: Gmail app password

### Frontend

- `REACT_APP_API_URL`: URL of the backend API

## License

[MIT License](LICENSE)

# 🚀 Render Deployment Instructions

## 1. Setup
- Ensure you have a `render.yaml` file in your project root (already provided).
- Create a PostgreSQL database on Render and copy its connection string.

## 2. Backend (Django)
- Deploy as a Web Service on Render.
- Set build command: `./build.sh`
- Set start command: `gunicorn mengedmate.wsgi:application`
- Set environment variables as in `render.yaml` (SECRET_KEY, DEBUG, ALLOWED_HOSTS, DATABASE_URL, CORS_ALLOWED_ORIGINS, FRONTEND_URL, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD).

## 3. Frontend (React)
- Deploy as a Static Site on Render.
- Set build command: `cd frontend && npm install && npm run build`
- Set publish directory: `frontend/build`
- Create a file `frontend/.env.production` with:
  ```
  REACT_APP_API_URL=https://<your-backend-domain>.onrender.com
  ```
- Set the same value in the Render dashboard as an environment variable for the static site if needed.

## 4. CORS
- In Django settings, ensure `CORS_ALLOWED_ORIGINS` includes your frontend Render URL.

## 5. Static/Media Files
- Django will serve static files using WhiteNoise. Media files will be served from `/media/`.
