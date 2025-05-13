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

## Deployment on Render

This application is configured for deployment on Render using the `render.yaml` file, which sets up separate services for the frontend and backend.

### Prerequisites

1. A Render account
2. A GitHub repository with your code

### Deployment Steps

1. Push your code to GitHub
2. Log in to your Render account
3. Click on "New" and select "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` file and set up the services:
   - `mengedmate-api`: The Django backend
   - `mengedmate-web`: The React frontend
   - `mengedmate-db`: The PostgreSQL database
6. Configure the environment variables:
   - `SECRET_KEY`: A secure random string
   - `EMAIL_HOST_USER`: Your Gmail address
   - `EMAIL_HOST_PASSWORD`: Your Gmail app password
7. Deploy the services

### Manual Deployment

If you prefer to set up the services manually:

#### Backend (Django API)

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the build command to `./build.sh`
4. Set the start command to `gunicorn mengedmate.wsgi:application`
5. Add the required environment variables:
   - `SECRET_KEY`: A secure random string
   - `DEBUG`: Set to 'False' for production
   - `ALLOWED_HOSTS`: Add your Render domains (e.g., `.onrender.com`)
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `CORS_ALLOWED_ORIGINS`: Your frontend URL (e.g., `https://mengedmate-web.onrender.com`)
   - `FRONTEND_URL`: Your frontend URL (e.g., `https://mengedmate-web.onrender.com`)
   - `EMAIL_HOST_USER`: Your Gmail address
   - `EMAIL_HOST_PASSWORD`: Your Gmail app password
6. Deploy the service

#### Frontend (React Web App)

1. Create a new Static Site on Render
2. Connect your GitHub repository
3. Set the build command to `cd frontend && npm install && npm run build`
4. Set the publish directory to `frontend/build`
5. Add the environment variables:
   - `REACT_APP_API_URL`: Your backend URL (e.g., `https://mengedmate-api.onrender.com`)
6. Add a redirect rule:
   - Source: `/*`
   - Destination: `/index.html`
7. Deploy the service

#### Database (PostgreSQL)

1. Create a new PostgreSQL database on Render
2. Note the connection details to use in your backend service

### Troubleshooting

If you encounter a 400 Bad Request error:

1. Check the CORS settings in the backend
2. Verify that the frontend is using the correct API URL
3. Check the browser console for specific error messages
4. Ensure that the backend is properly configured to accept requests from the frontend domain

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
