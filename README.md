# ⚡ MengedMate - EV Charging Station Management Platform

<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=500&size=30&pause=1000&color=4263EB&center=true&vCenter=true&width=600&height=80&lines=EV+Charging+Made+Easy;Station+Management+Platform;React+%7C+Django+%7C+PostgreSQL" alt="Typing SVG" />
</div>

## 🚀 About MengedMate

MengedMate is a comprehensive EV charging station management platform that connects electric vehicle owners with charging station operators. Built with modern web technologies, it provides a seamless experience for both EV drivers looking for charging stations and business owners managing their charging infrastructure.

## 🛠️ Tech Stack

<div align="center">

  ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
  ![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
  ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
  ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
  ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)

</div>

## 🌟 Key Features

### For EV Drivers
- 🔍 **Station Locator**: Find nearby charging stations with real-time availability
- 📱 **Mobile-Responsive**: Seamless experience across all devices
- 👤 **User Profiles**: Manage vehicle information and charging preferences
- 🔔 **Notifications**: Get alerts about charging status and station updates
- ⚡ **Multiple Car Profiles**: Support for multiple vehicles with different specifications

### For Station Owners
- 🏢 **Business Dashboard**: Comprehensive management interface
- 📊 **Analytics**: Track usage, revenue, and performance metrics
- 🔧 **Station Management**: Add, edit, and monitor charging stations
- ✅ **Verification System**: Build trust with verified business profiles
- 💰 **Revenue Tracking**: Monitor earnings and payment processing

## 📁 Project Structure

```
MengedMate/
├── backend/                 # Django REST API
│   ├── mengedmate/         # Main Django project
│   ├── authentication/     # User authentication app
│   ├── station_owners/     # Station owner management
│   ├── stations/           # Charging station data
│   └── requirements.txt    # Python dependencies
├── web_frontend/           # React web application (JSX)
│   ├── src/
│   │   ├── components/     # React components (JSX)
│   │   ├── services/       # API service layer (JSX)
│   │   └── App.jsx         # Main app component
│   └── package.json        # Node.js dependencies
├── mobile_frontend/        # Flutter mobile app
│   ├── lib/               # Dart source code
│   └── pubspec.yaml       # Flutter dependencies
└── README.md              # Project documentation
```

## 🔧 Technical Architecture

### Backend (Django REST API)
- **Framework**: Django 4.x with Django REST Framework
- **Authentication**: Token-based authentication with email verification
- **Database**: PostgreSQL (production), SQLite (development)
- **File Handling**: WhiteNoise for static files
- **Server**: Gunicorn for production deployment
- **API Documentation**: Auto-generated with DRF

### Frontend (React JSX)
- **Framework**: React 18+ with JSX components
- **Routing**: React Router for navigation
- **HTTP Client**: Axios for API communication
- **Styling**: Modern CSS with responsive design
- **Build Tool**: Create React App with JSX support
- **Backend Integration**: https://mengedmate.onrender.com/api

### Mobile (Flutter)
- **Framework**: Flutter with Dart
- **State Management**: Provider pattern
- **HTTP Client**: Dio for API requests
- **Maps Integration**: Google Maps API
- **Platform**: iOS and Android support

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

### Web Frontend Setup (React JSX)

1. Navigate to the web frontend directory:

```bash
cd web_frontend
```

2. Install dependencies:

```bash
npm install
```

3. Create environment file for development:

```bash
echo "REACT_APP_API_URL=http://localhost:8000" > .env.local
```

4. Start the React development server:

```bash
npm start
```

The web frontend will be running at http://localhost:3000/

### Mobile Frontend Setup (Flutter)

1. Navigate to the mobile frontend directory:

```bash
cd mobile_frontend
```

2. Install Flutter dependencies:

```bash
flutter pub get
```

3. Run the mobile app:

```bash
flutter run
```

## 🔗 API Endpoints

### Authentication
- `POST /api/auth/register/` - Register a new user
- `POST /api/auth/verify-email/` - Verify email with verification code
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/resend-verification/` - Resend email verification code
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile
- `PUT /api/auth/change-password/` - Change user password
- `POST /api/auth/forgot-password/` - Request password reset
- `POST /api/auth/reset-password/` - Reset password with token

### Station Owners
- `POST /api/station-owners/register/` - Register station owner
- `POST /api/station-owners/verify-email/` - Verify station owner email
- `GET /api/station-owners/profile/` - Get station owner profile
- `PATCH /api/station-owners/profile/` - Update station owner profile
- `POST /api/station-owners/login/` - Station owner login

### Charging Stations
- `GET /api/stations/` - List all charging stations
- `POST /api/stations/` - Create new charging station
- `GET /api/stations/{id}/` - Get specific station details
- `PATCH /api/stations/{id}/` - Update station information
- `DELETE /api/stations/{id}/` - Delete charging station
- `GET /api/stations/nearby/` - Find nearby stations
- `GET /api/stations/search/` - Search stations by criteria

### Connectors
- `GET /api/stations/{id}/connectors/` - List station connectors
- `POST /api/stations/{id}/connectors/` - Add connector to station
- `GET /api/connectors/{id}/` - Get connector details
- `PATCH /api/connectors/{id}/` - Update connector information
- `DELETE /api/connectors/{id}/` - Remove connector

### Notifications
- `GET /api/auth/notifications/` - Get user notifications
- `POST /api/auth/notifications/{id}/mark-read/` - Mark notification as read
- `POST /api/auth/notifications/mark-read/` - Mark all notifications as read
- `DELETE /api/auth/notifications/{id}/delete/` - Delete notification
- `POST /api/auth/notifications/test/` - Create test notification

### User Management
- `GET /api/users/` - List users (admin only)
- `GET /api/users/{id}/` - Get user details
- `PATCH /api/users/{id}/` - Update user information
- `DELETE /api/users/{id}/` - Delete user account

### Car Profiles
- `GET /api/auth/car-profiles/` - Get user car profiles
- `POST /api/auth/car-profiles/` - Create new car profile
- `GET /api/auth/car-profiles/{id}/` - Get specific car profile
- `PATCH /api/auth/car-profiles/{id}/` - Update car profile
- `DELETE /api/auth/car-profiles/{id}/` - Delete car profile
- `POST /api/auth/car-profiles/{id}/set-active/` - Set active car profile

### Reviews and Ratings
- `GET /api/stations/{id}/reviews/` - Get station reviews
- `POST /api/stations/{id}/reviews/` - Add station review
- `GET /api/reviews/{id}/` - Get review details
- `PATCH /api/reviews/{id}/` - Update review
- `DELETE /api/reviews/{id}/` - Delete review

### Booking and Reservations
- `GET /api/bookings/` - Get user bookings
- `POST /api/bookings/` - Create new booking
- `GET /api/bookings/{id}/` - Get booking details
- `PATCH /api/bookings/{id}/` - Update booking
- `DELETE /api/bookings/{id}/` - Cancel booking
- `POST /api/bookings/{id}/check-in/` - Check in to station
- `POST /api/bookings/{id}/check-out/` - Check out from station

### Analytics and Reports
- `GET /api/station-owners/analytics/` - Get station analytics
- `GET /api/station-owners/revenue/` - Get revenue reports
- `GET /api/station-owners/usage-stats/` - Get usage statistics
- `GET /api/stations/{id}/analytics/` - Get specific station analytics

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

### Web Frontend Development (React JSX)

To add new features to the web frontend:

1. Create new JSX components in the `web_frontend/src/components` directory
2. Add routes in `App.jsx`
3. Create services for API calls in `web_frontend/src/services` directory
4. Use JSX file extensions for all React components
5. Import components with `.jsx` extension: `import Component from './Component.jsx'`

### Mobile Frontend Development (Flutter)

To add new features to the mobile app:

1. Create new Dart files in the `mobile_frontend/lib` directory
2. Add routes in the main router configuration
3. Create services for API calls in the `lib/services` directory
4. Follow Flutter's widget-based architecture

## Environment Variables

### Backend
- `SECRET_KEY` - Django secret key
- `DEBUG` - Set to 'True' for development, 'False' for production
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DATABASE_URL` - PostgreSQL connection string (production only)
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of allowed origins for CORS
- `FRONTEND_URL` - URL of the frontend application
- `EMAIL_HOST_USER` - Gmail address for sending emails
- `EMAIL_HOST_PASSWORD` - Gmail app password

### Frontend
- `REACT_APP_API_URL` - URL of the backend API

## 👨‍💻 Developer

**Haile Abateneh** - Full Stack Developer
- 📧 Email: Halazab16@gmail.com
- 🌐 Portfolio: [haileab.onrender.com](https://haileab.onrender.com/)
- 💼 Specializing in Django, React, and Flutter development

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
