# MengedMate Payments App

A comprehensive payment system for MengedMate EV charging platform with Safaricom Ethiopia M-Pesa integration.

## Features

- **Multiple Payment Methods**: M-Pesa, TeleBirr, Bank Transfer, Credit Card
- **Digital Wallet**: User wallet system with balance management
- **Transaction Management**: Complete transaction lifecycle tracking
- **Safaricom Ethiopia Integration**: STK Push and callback handling
- **Payment Sessions**: Secure payment session management
- **Real-time Callbacks**: Webhook handling for payment confirmations

## Models

### PaymentMethod
- User payment method preferences
- Support for multiple payment types
- Default payment method selection

### Transaction
- Complete transaction records
- Status tracking (pending, processing, completed, failed)
- External reference linking

### Wallet
- User digital wallet
- Balance management
- Multi-currency support

### WalletTransaction
- Wallet transaction history
- Credit/debit tracking
- Balance snapshots

### PaymentSession
- Secure payment sessions
- STK Push request tracking
- Session expiration management

## API Endpoints

### Payment Methods
- `GET /api/payments/payment-methods/` - List user payment methods
- `POST /api/payments/payment-methods/` - Create payment method
- `GET /api/payments/payment-methods/{id}/` - Get payment method details
- `PUT /api/payments/payment-methods/{id}/` - Update payment method
- `DELETE /api/payments/payment-methods/{id}/` - Delete payment method

### Transactions
- `GET /api/payments/transactions/` - List user transactions
- `GET /api/payments/transactions/{id}/` - Get transaction details

### Wallet
- `GET /api/payments/wallet/` - Get user wallet details
- `GET /api/payments/wallet/transactions/` - Get wallet transaction history

### Payment Operations
- `POST /api/payments/initiate/` - Initiate M-Pesa payment
- `POST /api/payments/callback/` - Payment callback endpoint
- `POST /api/payments/status/` - Check transaction status

### Payment Sessions
- `GET /api/payments/sessions/` - List payment sessions

## Safaricom Ethiopia Integration

### Configuration
Set environment variables:
```
SAFARICOM_CONSUMER_KEY=your_consumer_key
SAFARICOM_CONSUMER_SECRET=your_consumer_secret
SAFARICOM_BUSINESS_SHORT_CODE=your_shortcode
SAFARICOM_PASSKEY=your_passkey
SAFARICOM_CALLBACK_URL=https://yourdomain.com/api/payments/callback/
SAFARICOM_USE_SANDBOX=True
```

### STK Push Flow
1. User initiates payment
2. System creates payment session
3. STK Push request sent to Safaricom
4. User receives M-Pesa prompt
5. User confirms payment
6. Safaricom sends callback
7. System processes callback and updates transaction

### Callback Handling
- Automatic transaction status updates
- Wallet balance updates on successful payments
- Error handling for failed transactions

## Usage Examples

### Initiate Payment
```json
POST /api/payments/initiate/
{
    "amount": "100.00",
    "phone_number": "+251912345678",
    "description": "EV Charging Payment"
}
```

### Create Payment Method
```json
POST /api/payments/payment-methods/
{
    "method_type": "mpesa",
    "phone_number": "+251912345678",
    "is_default": true
}
```

### Check Wallet Balance
```json
GET /api/payments/wallet/
Response:
{
    "id": "uuid",
    "balance": "150.00",
    "currency": "ETB",
    "is_active": true
}
```

## Security Features

- Token-based authentication
- Secure callback validation
- Transaction reference verification
- User isolation (users can only access their own data)

## Testing

Run payment tests:
```bash
python manage.py test payments
python manage.py test_payments
```

## Error Handling

- Comprehensive error responses
- Transaction failure recovery
- Callback validation
- Phone number format validation

## Monitoring

- Transaction status tracking
- Payment session monitoring
- Wallet balance auditing
- Failed payment alerts
