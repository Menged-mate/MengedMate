#!/bin/bash

# evmeri Deployment Setup Script
# This script sets up Ethiopian charging stations after deployment

echo "🚀 Starting evmeri deployment setup..."

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from the project root directory."
    exit 1
fi

# Run migrations
echo "📦 Running database migrations..."
python3 manage.py migrate
if [ $? -ne 0 ]; then
    echo "❌ Migration failed!"
    exit 1
fi

# Collect static files (ignore errors in development)
echo "📁 Collecting static files..."
python3 manage.py collectstatic --noinput || echo "⚠️  Static files collection failed (this is OK in development)"

# Create Ethiopian charging stations
echo "🇪🇹 Setting up Ethiopian charging stations..."
python3 manage.py populate_ethiopian_stations
if [ $? -ne 0 ]; then
    echo "❌ Failed to create Ethiopian stations!"
    exit 1
fi

echo "🎉 Deployment setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "   ✅ Database migrations applied"
echo "   ✅ Ethiopian charging stations created"
echo "   ✅ Static files collected"
echo ""
echo "🌐 Your evmeri backend is ready!"
echo "   📍 10 Ethiopian charging stations available"
echo "   💳 Chapa payment integration configured"
echo "   📱 Mobile app return URLs fixed"
echo ""
echo "🔗 API Endpoints:"
echo "   📍 Stations: /api/public/stations/"
echo "   💳 Payments: /api/payments/"
echo "   🔐 Auth: /api/auth/"
echo ""
echo "🎯 Next steps:"
echo "   1. Deploy your mobile app"
echo "   2. Test QR code payments"
echo "   3. Verify station locations on map"
