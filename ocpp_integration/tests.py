from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch, Mock, AsyncMock
from .models import OCPPChargePoint, OCPPTransaction, OCPPConnector
from .services import OCPPService
from .client import OCPPClient
from charging_stations.models import ChargingStation, Connector
from decimal import Decimal
import asyncio
import json

User = get_user_model()


class OCPPChargePointModelTests(TestCase):
    """Test cases for OCPPChargePoint model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Main Street',
            latitude=9.0320,
            longitude=38.7469,
            owner=self.user
        )
        self.charge_point_data = {
            'charge_point_id': 'CP001',
            'station': self.station,
            'vendor': 'TestVendor',
            'model': 'TestModel',
            'serial_number': 'SN123456',
            'firmware_version': '1.0.0',
            'status': 'available'
        }

    def test_create_charge_point(self):
        """Test creating an OCPP charge point"""
        charge_point = OCPPChargePoint.objects.create(**self.charge_point_data)
        self.assertEqual(charge_point.charge_point_id, 'CP001')
        self.assertEqual(charge_point.station, self.station)
        self.assertEqual(charge_point.vendor, 'TestVendor')
        self.assertEqual(charge_point.status, 'available')
        self.assertTrue(charge_point.is_online)

    def test_charge_point_string_representation(self):
        """Test charge point string representation"""
        charge_point = OCPPChargePoint.objects.create(**self.charge_point_data)
        expected = f"CP001 - Test Station"
        self.assertEqual(str(charge_point), expected)

    def test_charge_point_heartbeat_update(self):
        """Test charge point heartbeat update"""
        charge_point = OCPPChargePoint.objects.create(**self.charge_point_data)
        original_heartbeat = charge_point.last_heartbeat

        # Simulate heartbeat update
        charge_point.update_heartbeat()
        charge_point.refresh_from_db()

        self.assertGreater(charge_point.last_heartbeat, original_heartbeat)
        self.assertTrue(charge_point.is_online)


class OCPPConnectorModelTests(TestCase):
    """Test cases for OCPPConnector model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Main Street',
            latitude=9.0320,
            longitude=38.7469,
            owner=self.user
        )
        self.charge_point = OCPPChargePoint.objects.create(
            charge_point_id='CP001',
            station=self.station,
            vendor='TestVendor',
            model='TestModel'
        )
        self.connector = Connector.objects.create(
            station=self.station,
            connector_type='Type2',
            power_output=22.0,
            price_per_kwh=Decimal('15.50')
        )
        self.ocpp_connector_data = {
            'charge_point': self.charge_point,
            'connector': self.connector,
            'connector_id': 1,
            'status': 'Available',
            'error_code': 'NoError'
        }

    def test_create_ocpp_connector(self):
        """Test creating an OCPP connector"""
        ocpp_connector = OCPPConnector.objects.create(**self.ocpp_connector_data)
        self.assertEqual(ocpp_connector.charge_point, self.charge_point)
        self.assertEqual(ocpp_connector.connector, self.connector)
        self.assertEqual(ocpp_connector.connector_id, 1)
        self.assertEqual(ocpp_connector.status, 'Available')

    def test_ocpp_connector_string_representation(self):
        """Test OCPP connector string representation"""
        ocpp_connector = OCPPConnector.objects.create(**self.ocpp_connector_data)
        expected = f"CP001 - Connector 1"
        self.assertEqual(str(ocpp_connector), expected)

    def test_connector_status_update(self):
        """Test connector status update"""
        ocpp_connector = OCPPConnector.objects.create(**self.ocpp_connector_data)

        # Update status
        ocpp_connector.update_status('Occupied', 'NoError')
        self.assertEqual(ocpp_connector.status, 'Occupied')
        self.assertEqual(ocpp_connector.error_code, 'NoError')


class OCPPTransactionModelTests(TestCase):
    """Test cases for OCPPTransaction model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.ev_user = User.objects.create_user(
            email='evuser@example.com',
            password='testpass123'
        )
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Main Street',
            latitude=9.0320,
            longitude=38.7469,
            owner=self.user
        )
        self.charge_point = OCPPChargePoint.objects.create(
            charge_point_id='CP001',
            station=self.station,
            vendor='TestVendor',
            model='TestModel'
        )
        self.connector = Connector.objects.create(
            station=self.station,
            connector_type='Type2',
            power_output=22.0,
            price_per_kwh=Decimal('15.50')
        )
        self.ocpp_connector = OCPPConnector.objects.create(
            charge_point=self.charge_point,
            connector=self.connector,
            connector_id=1
        )
        self.transaction_data = {
            'transaction_id': 12345,
            'charge_point': self.charge_point,
            'connector': self.ocpp_connector,
            'user': self.ev_user,
            'id_tag': 'USER123',
            'meter_start': 1000,
            'status': 'active'
        }

    def test_create_ocpp_transaction(self):
        """Test creating an OCPP transaction"""
        transaction = OCPPTransaction.objects.create(**self.transaction_data)
        self.assertEqual(transaction.transaction_id, 12345)
        self.assertEqual(transaction.charge_point, self.charge_point)
        self.assertEqual(transaction.user, self.ev_user)
        self.assertEqual(transaction.status, 'active')

    def test_transaction_string_representation(self):
        """Test transaction string representation"""
        transaction = OCPPTransaction.objects.create(**self.transaction_data)
        expected = f"Transaction 12345 - CP001"
        self.assertEqual(str(transaction), expected)

    def test_transaction_energy_calculation(self):
        """Test transaction energy calculation"""
        transaction = OCPPTransaction.objects.create(**self.transaction_data)

        # Set meter stop value
        transaction.meter_stop = 1500
        transaction.save()

        # Calculate energy consumed
        energy_consumed = transaction.get_energy_consumed()
        self.assertEqual(energy_consumed, 500)  # 1500 - 1000 = 500 Wh

    def test_transaction_cost_calculation(self):
        """Test transaction cost calculation"""
        transaction = OCPPTransaction.objects.create(**self.transaction_data)
        transaction.meter_stop = 1500  # 500 Wh = 0.5 kWh
        transaction.save()

        # Calculate cost (0.5 kWh * 15.50 ETB/kWh = 7.75 ETB)
        cost = transaction.calculate_cost()
        expected_cost = Decimal('7.75')
        self.assertEqual(cost, expected_cost)
