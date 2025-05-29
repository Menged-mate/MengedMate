from django.urls import path
from . import views

urlpatterns = [
    path('payment-methods/', views.PaymentMethodListCreateView.as_view(), name='payment-methods'),
    path('payment-methods/<uuid:pk>/', views.PaymentMethodDetailView.as_view(), name='payment-method-detail'),
    
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('transactions/<uuid:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    
    path('wallet/', views.WalletDetailView.as_view(), name='wallet'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),
    
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('callback/', views.payment_callback, name='payment-callback'),
    path('status/', views.TransactionStatusView.as_view(), name='transaction-status'),
    
    path('sessions/', views.PaymentSessionListView.as_view(), name='payment-sessions'),
]
