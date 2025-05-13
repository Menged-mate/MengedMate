# EV Charging Station Locator

A web application to locate EV charging stations with email verification authentication.

## Features

- User authentication with email verification
- Mobile-responsive design
- EV charging station locator (coming soon)

## Tech Stack

### Backend
- Django
- Django Rest Framework (DRF)
- Django Allauth for authentication

### Frontend
- React
- React Router
- Axios for API requests

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

## License

[MIT License](LICENSE)
