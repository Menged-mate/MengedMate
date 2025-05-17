from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    class EVConnectorType(models.TextChoices):
        TYPE_1 = 'type1', _('Type 1 (J1772)')
        TYPE_2 = 'type2', _('Type 2 (Mennekes)')
        CCS1 = 'ccs1', _('CCS Combo 1')
        CCS2 = 'ccs2', _('CCS Combo 2')
        CHADEMO = 'chademo', _('CHAdeMO')
        TESLA = 'tesla', _('Tesla')
        OTHER = 'other', _('Other')
        NONE = 'none', _('None')

    username = None
    email = models.EmailField(_('email address'), unique=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    ev_battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True,
                                                 help_text=_('Battery capacity in kWh'))
    ev_connector_type = models.CharField(max_length=20, choices=EVConnectorType.choices,
                                        default=EVConnectorType.NONE, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
