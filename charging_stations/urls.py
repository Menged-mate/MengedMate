from django.urls import path
from .views import (
    StationOwnerRegistrationView,
    StationOwnerVerifyEmailView,
    StationOwnerProfileView,
    ChargingStationListCreateView,
    ChargingStationDetailView,
    ConnectorCreateView,
    ConnectorDetailView,
    StationImageCreateView,
    StationQRCodesView,
    ConnectorQRCodeView,
    DownloadQRCodeView,
    AppContentView,
    StationReviewListCreateView,
    StationReviewDetailView,
    UserReviewsView,
    StationReviewStatsView,
    StationOwnerReviewsView,
    ReviewReplyCreateView,
    ReviewReplyDetailView,
    StationOwnerRepliesView,
    AvailableStationsView,
    MobileChargingHistoryView,
    StationOwnerSettingsView,
    NotificationTemplateListView,
    NotificationTemplateDetailView,
    PayoutMethodListCreateView,
    PayoutMethodDetailView,
    SetDefaultPayoutMethodView,
    WithdrawalRequestView
)
from .map_views import (
    PublicStationListView,
    NearbyStationsView,
    StationSearchView,
    PublicStationDetailView,
    FavoriteStationListView,
    FavoriteStationToggleView
)
from .home_views import HomeView, AppConfigView
from .dashboard_views import (
    DashboardStatsView,
    ActivitiesView,
    AnalyticsUsageView,
    NotificationsView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    AnalyticsReportsView,
    RevenueTransactionsView,
    RevenueDetailView
)

app_name = 'charging_stations'

urlpatterns = [
    path('station-owners/register/', StationOwnerRegistrationView.as_view(), name='station-owner-register'),
    path('station-owners/verify-email/', StationOwnerVerifyEmailView.as_view(), name='station-owner-verify-email'),
    path('station-owners/profile/', StationOwnerProfileView.as_view(), name='station-owner-profile'),

    path('stations/', ChargingStationListCreateView.as_view(), name='station-list-create'),
    path('stations/<uuid:id>/', ChargingStationDetailView.as_view(), name='station-detail'),
    path('stations/<uuid:station_id>/connectors/', ConnectorCreateView.as_view(), name='connector-create'),
    path('stations/<uuid:station_id>/connectors/<uuid:id>/', ConnectorDetailView.as_view(), name='connector-detail'),
    path('stations/<uuid:station_id>/images/', StationImageCreateView.as_view(), name='station-image-create'),

    path('stations/<uuid:station_id>/qr-codes/', StationQRCodesView.as_view(), name='station-qr-codes'),
    path('connectors/<uuid:connector_id>/qr-code/', ConnectorQRCodeView.as_view(), name='connector-qr-code'),
    path('connectors/<uuid:connector_id>/qr-code/download/', DownloadQRCodeView.as_view(), name='download-qr-code'),

    path('public/stations/', PublicStationListView.as_view(), name='public-station-list'),
    path('public/stations/<uuid:id>/', PublicStationDetailView.as_view(), name='public-station-detail'),
    path('public/nearby-stations/', NearbyStationsView.as_view(), name='nearby-stations'),
    path('public/search-stations/', StationSearchView.as_view(), name='search-stations'),
    path('favorites/', FavoriteStationListView.as_view(), name='favorite-list'),
    path('favorites/<uuid:station_id>/toggle/', FavoriteStationToggleView.as_view(), name='favorite-toggle'),

    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('activities/', ActivitiesView.as_view(), name='activities'),
    path('analytics/usage/', AnalyticsUsageView.as_view(), name='analytics-usage'),
    path('analytics/reports/', AnalyticsReportsView.as_view(), name='analytics-reports'),
    path('revenue/transactions/', RevenueTransactionsView.as_view(), name='revenue-transactions'),
    path('revenue/details/', RevenueDetailView.as_view(), name='revenue-details'),
    path('notifications/', NotificationsView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', MarkNotificationReadView.as_view(), name='mark-notification-read'),
    path('notifications/mark-all-read/', MarkAllNotificationsReadView.as_view(), name='mark-all-notifications-read'),

    path('app-content/', AppContentView.as_view(), name='app-content-list'),
    path('app-content/<str:content_type>/', AppContentView.as_view(), name='app-content-detail'),

    path('stations/<uuid:station_id>/reviews/', StationReviewListCreateView.as_view(), name='station-reviews'),
    path('reviews/<int:id>/', StationReviewDetailView.as_view(), name='review-detail'),
    path('my-reviews/', UserReviewsView.as_view(), name='user-reviews'),
    path('stations/<uuid:station_id>/review-stats/', StationReviewStatsView.as_view(), name='station-review-stats'),
    path('stations/reviews/', StationOwnerReviewsView.as_view(), name='station-owner-reviews'),

    # Review reply endpoints
    path('reviews/reply/', ReviewReplyCreateView.as_view(), name='review-reply-create'),
    path('reviews/reply/<int:id>/', ReviewReplyDetailView.as_view(), name='review-reply-detail'),
    path('my-replies/', StationOwnerRepliesView.as_view(), name='station-owner-replies'),

    # Available stations endpoint
    path('available-stations/', AvailableStationsView.as_view(), name='available-stations'),
    path('mobile/charging-history/', MobileChargingHistoryView.as_view(), name='mobile-charging-history'),

    # Settings endpoints
    path('settings/', StationOwnerSettingsView.as_view(), name='station-owner-settings'),
    path('notification-templates/', NotificationTemplateListView.as_view(), name='notification-templates'),
    path('notification-templates/<str:template_type>/', NotificationTemplateDetailView.as_view(), name='notification-template-detail'),

    # Payout methods endpoints
    path('payout-methods/', PayoutMethodListCreateView.as_view(), name='payout-methods'),
    path('payout-methods/<int:id>/', PayoutMethodDetailView.as_view(), name='payout-method-detail'),
    path('payout-methods/<int:method_id>/set-default/', SetDefaultPayoutMethodView.as_view(), name='set-default-payout-method'),

    # Withdrawal endpoints
    path('withdrawals/', WithdrawalRequestView.as_view(), name='withdrawal-request'),
]