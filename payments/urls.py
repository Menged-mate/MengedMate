from django.urls import path
from . import views

urlpatterns = [
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('transactions/<uuid:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),

    path('wallet/', views.WalletDetailView.as_view(), name='wallet'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),

    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('callback/', views.payment_callback, name='payment-callback'),
    path('mobile-return/', views.MobileReturnView.as_view(), name='mobile-return'),
    path('status/', views.TransactionStatusView.as_view(), name='transaction-status'),
    path('process-pending-credits/', views.process_pending_credits, name='process-pending-credits'),
    path('check-wallet-status/', views.check_wallet_status, name='check-wallet-status'),

    path('qr-info/<str:qr_token>/', views.QRConnectorInfoView.as_view(), name='qr-connector-info'),
    path('qr-initiate/<str:qr_token>/', views.QRPaymentInitiateView.as_view(), name='qr-payment-initiate'),
    path('qr-sessions/', views.QRPaymentSessionListView.as_view(), name='qr-payment-sessions'),
    path('qr-sessions/<str:session_token>/', views.QRPaymentSessionDetailView.as_view(), name='qr-payment-session-detail'),
    path('qr-sessions/<str:session_token>/start-charging/', views.StartChargingFromQRView.as_view(), name='start-charging-from-qr'),
    path('qr-sessions/<str:session_token>/stop-charging/', views.StopChargingFromQRView.as_view(), name='stop-charging-from-qr'),
    path('qr-sessions/<str:session_token>/test-complete/', views.TestCompletePaymentView.as_view(), name='test-complete-payment'),
    path('qr-sessions/<str:session_token>/test-create-charging/', views.TestCreateChargingSessionView.as_view(), name='test-create-charging'),
    path('withdrawals/', views.WithdrawalView.as_view(), name='withdrawals'),

    path('charging-history/', views.ChargingHistoryView.as_view(), name='charging-history'),
]
