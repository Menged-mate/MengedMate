# MengedMate - Electric Vehicle Charging Station Management Platform

MengedMate is a comprehensive platform for managing electric vehicle charging stations across Ethiopia. The platform connects station owners with EV drivers, providing real-time station monitoring, payment processing, and analytics.

## Overview

MengedMate serves as the bridge between electric vehicle charging infrastructure and users in Ethiopia. Station owners can register their charging stations, monitor usage, track revenue, and manage operations through an intuitive dashboard. EV drivers can find nearby stations, check availability, make reservations, and process payments seamlessly.

## Key Features

### For Station Owners
- **Station Management**: Register and manage multiple charging stations with detailed information
- **Real-time Monitoring**: Track station status, connector availability, and usage patterns
- **Revenue Analytics**: Comprehensive financial reporting with transaction history and revenue trends
- **Payment Processing**: Integrated M-Pesa payment system for seamless transactions
- **Wallet Management**: Digital wallet for receiving payments and managing payouts
- **Maintenance Tracking**: Monitor station health and schedule maintenance activities
- **User Notifications**: Real-time alerts for station events and system updates

### For EV Drivers
- **Station Discovery**: Find nearby charging stations with real-time availability
- **Route Planning**: Integrated mapping for optimal charging route planning
- **Reservation System**: Book charging slots in advance to guarantee availability
- **Payment Integration**: Secure payment processing through M-Pesa and other methods
- **Session Tracking**: Monitor charging progress and receive completion notifications
- **Rating System**: Rate and review charging stations for community feedback

### Platform Features
- **Multi-language Support**: Available in English and Amharic
- **Mobile Responsive**: Optimized for desktop, tablet, and mobile devices
- **Real-time Updates**: Live status updates for stations and charging sessions
- **Advanced Analytics**: Detailed reporting and insights for business intelligence
- **Secure Authentication**: Multi-factor authentication and secure user management
- **API Integration**: RESTful APIs for third-party integrations

## Technology Stack

### Backend
- **Framework**: Django 4.2 with Django REST Framework
- **Database**: PostgreSQL for production, SQLite for development
- **Authentication**: Token-based authentication with email verification
- **Payment Processing**: Safaricom Ethiopia M-Pesa integration
- **File Storage**: AWS S3 for production media files
- **Caching**: Redis for session management and caching
- **Task Queue**: Celery for background task processing

### Frontend
- **Framework**: React 18 with modern hooks and functional components
- **Routing**: React Router for single-page application navigation
- **Styling**: Custom CSS with responsive design principles
- **State Management**: React hooks for local state management
- **HTTP Client**: Fetch API for backend communication
- **Charts**: Custom chart components for analytics visualization

### Infrastructure
- **Hosting**: Render.com for backend deployment
- **CDN**: Cloudflare for static asset delivery
- **Monitoring**: Built-in health checks and error tracking
- **Security**: HTTPS encryption and CORS configuration

## Installation and Setup

### Prerequisites
- Python 3.9 or higher
- Node.js 16 or higher
- PostgreSQL 12 or higher
- Redis server

### Backend Setup

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/your-username/mengedmate.git
cd mengedmate
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables by creating a `.env` file:

```bash
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://username:password@localhost:5432/mengedmate
REDIS_URL=redis://localhost:6379/0
SAFARICOM_CONSUMER_KEY=your-consumer-key
SAFARICOM_CONSUMER_SECRET=your-consumer-secret
SAFARICOM_BUSINESS_SHORT_CODE=your-shortcode
SAFARICOM_PASSKEY=your-passkey
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

Run database migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create a superuser account:

```bash
python manage.py createsuperuser
```

Start the development server:

```bash
python manage.py runserver
```

### Frontend Setup

Navigate to the frontend directory:

```bash
cd web_frontend
```

Install Node.js dependencies:

```bash
npm install
```

Start the development server:

```bash
npm start
```

The frontend will be available at `http://localhost:3000` and will proxy API requests to the Django backend at `http://localhost:8000`.

## API Documentation

### Authentication Endpoints

**User Registration**
- `POST /api/auth/register/` - Register a new user account
- `POST /api/auth/verify-email/` - Verify email address with verification code
- `POST /api/auth/resend-verification/` - Resend email verification code

**User Authentication**
- `POST /api/auth/login/` - User login with email and password
- `POST /api/auth/logout/` - User logout and token invalidation
- `POST /api/auth/forgot-password/` - Request password reset email
- `POST /api/auth/reset-password/` - Reset password with token

**Profile Management**
- `GET /api/auth/profile/` - Get user profile information
- `PUT /api/auth/profile/` - Update user profile details
- `PUT /api/auth/change-password/` - Change user password

### Station Owner Endpoints

**Registration and Profile**
- `POST /api/station-owners/register/` - Register as station owner
- `POST /api/station-owners/verify-email/` - Verify station owner email
- `GET /api/station-owners/profile/` - Get station owner profile
- `PATCH /api/station-owners/profile/` - Update station owner profile
- `POST /api/station-owners/login/` - Station owner login

### Charging Station Management

**Station Operations**
- `GET /api/stations/` - List all charging stations for owner
- `POST /api/stations/` - Create new charging station
- `GET /api/stations/{id}/` - Get specific station details
- `PATCH /api/stations/{id}/` - Update station information
- `DELETE /api/stations/{id}/` - Delete charging station

**Connector Management**
- `GET /api/stations/{id}/connectors/` - List station connectors
- `POST /api/stations/{id}/connectors/` - Add connector to station
- `GET /api/connectors/{id}/` - Get connector details
- `PATCH /api/connectors/{id}/` - Update connector information
- `DELETE /api/connectors/{id}/` - Remove connector

**Public Station Access**
- `GET /api/public/stations/` - List all public stations
- `GET /api/stations/nearby/` - Find nearby stations with location
- `GET /api/stations/search/` - Search stations by criteria
- `GET /api/public/stations/{id}/` - Get public station details

### Payment System

**Payment Processing**
- `POST /api/payments/initiate/` - Initiate M-Pesa payment
- `POST /api/payments/callback/` - Payment callback endpoint
- `POST /api/payments/status/` - Check transaction status

**Wallet Management**
- `GET /api/payments/wallet/` - Get wallet balance and details
- `GET /api/payments/wallet/transactions/` - List wallet transactions
- `POST /api/payments/wallet/withdraw/` - Withdraw funds from wallet

**Payment Methods**
- `GET /api/payments/payment-methods/` - List user payment methods
- `POST /api/payments/payment-methods/` - Add new payment method
- `PATCH /api/payments/payment-methods/{id}/` - Update payment method
- `DELETE /api/payments/payment-methods/{id}/` - Remove payment method

**Transaction History**
- `GET /api/payments/transactions/` - List all transactions
- `GET /api/payments/transactions/{id}/` - Get transaction details
- `GET /api/payments/sessions/` - List payment sessions

### Analytics and Reporting

**Dashboard Analytics**
- `GET /api/dashboard/` - Get dashboard statistics
- `GET /api/activities/` - Get recent activity feed
- `GET /api/analytics/usage/` - Get usage analytics
- `GET /api/analytics/reports/` - Get comprehensive analytics reports

**Notifications**
- `GET /api/notifications/` - Get user notifications
- `POST /api/notifications/{id}/mark-read/` - Mark notification as read
- `POST /api/notifications/mark-all-read/` - Mark all notifications as read
- `DELETE /api/notifications/{id}/` - Delete notification

### Vehicle Management

**User Vehicles**
- `GET /api/auth/vehicles/` - List user vehicles
- `POST /api/auth/vehicles/` - Add new vehicle
- `GET /api/auth/vehicles/{id}/` - Get vehicle details
- `PATCH /api/auth/vehicles/{id}/` - Update vehicle information
- `DELETE /api/auth/vehicles/{id}/` - Remove vehicle

## Project Structure

### Backend Structure
```
mengedmate/
├── authentication/          
├── charging_stations/       
├── payments/               
├── mengedmate/             
├── static/                
├── media/                
├── requirements.txt        
└── manage.py              
```

### Frontend Structure
```
web_frontend/
├── src/
│   ├── components/
│   │   ├── auth/           
│   │   ├── dashboard/      
│   │   ├── landing/        
│   │   ├── reports/        
│   │   ├── revenue/       
│   │   ├── stations/       
│   │   └── wallet/         
│   ├── styles/             
│   ├── App.jsx            
│   └── index.js           
└── package.json           
```

## Features in Detail

### Station Management System
Station owners can register multiple charging stations with comprehensive details including location, connector types, pricing, and operational hours. The system supports real-time status updates, allowing owners to mark stations as operational, under maintenance, or temporarily closed.

### Real-time Analytics Dashboard
The analytics dashboard provides comprehensive insights into station performance, revenue trends, energy consumption, and user behavior. Station owners can view data across different time periods and filter by specific stations for detailed analysis.

### Integrated Payment System
MengedMate integrates with Safaricom Ethiopia's M-Pesa system for seamless payment processing. Users can add funds to their digital wallet, pay for charging sessions, and station owners can receive payments directly to their accounts.

### Mobile-First Design
The platform is designed with a mobile-first approach, ensuring optimal user experience across all devices. The responsive design adapts to different screen sizes while maintaining functionality and usability.

### Multi-language Support
The platform supports both English and Amharic languages, making it accessible to a broader user base across Ethiopia. Language switching is seamless and preserves user session data.

## Security and Privacy

### Data Protection
All user data is encrypted in transit and at rest. The platform implements industry-standard security practices including secure password hashing, token-based authentication, and regular security audits.

### Payment Security
Payment processing follows PCI DSS compliance standards. All financial transactions are encrypted and processed through secure channels with Safaricom Ethiopia's certified payment gateway.

### User Privacy
The platform adheres to strict privacy policies, ensuring user data is only used for platform functionality and is never shared with third parties without explicit consent.

## Contributing

We welcome contributions to MengedMate. Please follow these guidelines when contributing:

1. Fork the repository and create a feature branch
2. Write clear, documented code following the existing style
3. Add tests for new functionality
4. Ensure all tests pass before submitting
5. Submit a pull request with a detailed description of changes

## Support and Documentation

For technical support, feature requests, or bug reports, please contact our development team. Additional documentation and API references are available in the project wiki.

## License

MengedMate is proprietary software developed for the Ethiopian electric vehicle charging infrastructure market. All rights reserved.

## Contact

For business inquiries, partnerships, or technical support, please reach out to our team through the official channels provided in the platform.
