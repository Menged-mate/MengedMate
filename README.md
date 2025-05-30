# MengedMate - EV Charging Station Management Platform

MengedMate is a comprehensive platform for managing electric vehicle charging stations, built with Django REST Framework backend and React frontend.

## Features

- **Station Management**: Add, edit, and manage charging stations
- **User Authentication**: Secure user registration and login
- **Payment Integration**: Chapa payment gateway integration
- **Real-time Dashboard**: Monitor station status and analytics
- **Mobile Responsive**: Works on all devices

## Payment Integration

### Chapa Payment Gateway

MengedMate uses Chapa as the primary payment gateway for processing transactions.

#### Configuration

Set the following environment variables:

```bash
CHAPA_SECRET_KEY=your_chapa_secret_key
CHAPA_PUBLIC_KEY=your_chapa_public_key
CHAPA_CALLBACK_URL=https://yourdomain.com/api/payments/callback/
CHAPA_RETURN_URL=https://yourdomain.com/payment/success
CHAPA_USE_SANDBOX=True  # Set to False for production
```

#### Supported Payment Methods

- Mobile Money (TeleBirr, M-Pesa)
- Bank Transfers
- Credit/Debit Cards
- Digital Wallets

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile

### Payments
- `POST /api/payments/initiate/` - Initiate payment
- `POST /api/payments/callback/` - Payment callback (webhook)
- `GET /api/payments/status/` - Check payment status
- `GET /api/payments/transactions/` - List transactions
- `GET /api/payments/wallet/` - Get wallet balance

### Charging Stations
- `GET /api/stations/` - List charging stations
- `POST /api/stations/` - Create charging station
- `GET /api/stations/{id}/` - Get station details
- `PUT /api/stations/{id}/` - Update station
- `DELETE /api/stations/{id}/` - Delete station

### Dashboard
- `GET /api/dashboard/` - Dashboard statistics
- `GET /api/activities/` - Recent activities
- `GET /api/analytics/usage/` - Usage analytics
- `GET /api/analytics/reports/` - Generate reports

## Installation

### Backend Setup

1. Clone the repository
2. Create virtual environment
3. Install dependencies
4. Set environment variables
5. Run migrations
6. Start development server

### Frontend Setup

1. Navigate to web_frontend directory
2. Install dependencies with npm
3. Start development server

## Technology Stack

### Backend
- Django 4.2+
- Django REST Framework
- PostgreSQL
- Chapa Payment Gateway
- JWT Authentication

### Frontend
- React 18+
- React Router
- Axios for API calls
- CSS3 with responsive design

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mengedmate

# Django
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.onrender.com

# Chapa Payment
CHAPA_SECRET_KEY=your_chapa_secret_key
CHAPA_PUBLIC_KEY=your_chapa_public_key
CHAPA_USE_SANDBOX=True

# Email
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# Frontend
FRONTEND_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## License

This project is licensed under the MIT License.