from django.core.management.base import BaseCommand
from charging_stations.models import AppContent


class Command(BaseCommand):
    help = 'Populate initial app content (About, Privacy Policy, Terms of Service)'

    def handle(self, *args, **options):
        # About MengedMate
        about_content = """
# About MengedMate

MengedMate is Ethiopia's leading electric vehicle charging network, dedicated to accelerating the adoption of sustainable transportation across the country.

## Our Mission
To build a comprehensive, reliable, and accessible electric vehicle charging infrastructure that supports Ethiopia's transition to clean energy transportation.

## What We Offer

### For EV Drivers
- **Extensive Network**: Access to charging stations across major cities and highways
- **Easy Payment**: Seamless QR code-based payment system
- **Real-time Information**: Live station availability and pricing
- **Mobile App**: User-friendly app for finding and managing charging sessions

### For Station Owners
- **Business Opportunity**: Join our network and generate revenue from EV charging
- **Management Tools**: Comprehensive dashboard for station and revenue management
- **Technical Support**: Full support for installation and maintenance
- **Marketing Support**: Promotion through our platform and mobile app

## Our Technology
- **Smart Charging**: Intelligent load management and optimization
- **OCPP Integration**: Industry-standard charging protocols
- **Mobile Payments**: Secure payment processing through Chapa
- **Real-time Monitoring**: 24/7 station monitoring and support

## Sustainability Commitment
MengedMate is committed to supporting Ethiopia's green energy goals by:
- Promoting electric vehicle adoption
- Supporting renewable energy integration
- Reducing carbon emissions from transportation
- Creating sustainable business opportunities

## Contact Us
For more information, partnerships, or support:
- Email: info@mengedmate.com
- Phone: +251-911-123-456
- Website: www.mengedmate.com

Join us in building a cleaner, more sustainable future for Ethiopian transportation!
        """

        privacy_policy_content = """
# Privacy Policy

**Last Updated: January 2024**

MengedMate ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our mobile application and web services.

## Information We Collect

### Personal Information
- **Account Information**: Name, email address, phone number
- **Payment Information**: Payment method details (processed securely through Chapa)
- **Location Data**: GPS location for finding nearby charging stations
- **Vehicle Information**: EV model and charging preferences

### Usage Information
- **Charging Sessions**: Station usage, charging duration, energy consumed
- **App Usage**: Features used, preferences, and interaction patterns
- **Device Information**: Device type, operating system, app version

## How We Use Your Information

### Service Provision
- Facilitate charging station access and payments
- Provide real-time station availability and navigation
- Process payments and generate receipts
- Customer support and communication

### Service Improvement
- Analyze usage patterns to improve our services
- Develop new features and functionality
- Optimize charging station network placement
- Enhance user experience

## Information Sharing

### We Do Not Sell Your Data
We never sell, rent, or trade your personal information to third parties.

### Limited Sharing
We may share information only in these circumstances:
- **Service Providers**: Trusted partners who help operate our services
- **Payment Processing**: Secure payment processors (Chapa)
- **Legal Requirements**: When required by law or to protect our rights
- **Business Transfers**: In case of merger or acquisition (with notice)

## Data Security

### Protection Measures
- **Encryption**: All data transmitted using industry-standard encryption
- **Secure Storage**: Data stored on secure, protected servers
- **Access Controls**: Limited access to personal information
- **Regular Audits**: Security assessments and updates

### Payment Security
- Payment information processed through PCI-compliant systems
- We do not store complete payment card information
- Tokenized payment processing for enhanced security

## Your Rights

### Access and Control
- **View Data**: Access your personal information
- **Update Information**: Modify your account details
- **Delete Account**: Request account deletion
- **Data Portability**: Export your data

### Privacy Controls
- **Location Services**: Control location data sharing
- **Notifications**: Manage communication preferences
- **Marketing**: Opt-out of promotional communications

## Data Retention
- Account information retained while account is active
- Charging session data retained for billing and support purposes
- Deleted accounts purged within 30 days
- Legal requirements may extend retention periods

## Children's Privacy
Our services are not intended for children under 13. We do not knowingly collect information from children under 13.

## International Users
Data may be processed in Ethiopia or other countries where our service providers operate, always with appropriate safeguards.

## Changes to Privacy Policy
We may update this policy periodically. Significant changes will be communicated through the app or email.

## Contact Us
For privacy questions or concerns:
- Email: privacy@mengedmate.com
- Phone: +251-911-123-456
- Address: Addis Ababa, Ethiopia

Your privacy is important to us, and we're committed to protecting your information while providing excellent service.
        """

        terms_of_service_content = """
# Terms of Service

**Last Updated: January 2024**

Welcome to MengedMate! These Terms of Service ("Terms") govern your use of our electric vehicle charging services, mobile application, and website.

## Acceptance of Terms
By using MengedMate services, you agree to these Terms. If you don't agree, please don't use our services.

## Service Description

### MengedMate Platform
- Electric vehicle charging network across Ethiopia
- Mobile app for finding and accessing charging stations
- Payment processing and session management
- Customer support and assistance

### Station Owner Services
- Platform for hosting and managing charging stations
- Revenue sharing and payment processing
- Marketing and customer acquisition support
- Technical and operational support

## User Accounts

### Account Creation
- Accurate information required for registration
- You're responsible for account security
- One account per person or business
- Must be 18+ years old to create an account

### Account Responsibilities
- Maintain current contact information
- Protect login credentials
- Report unauthorized access immediately
- Comply with all applicable laws

## Charging Services

### Station Access
- QR code scanning required for station access
- Payment required before charging begins
- Follow all station-specific rules and guidelines
- Respect other users and station property

### Payment Terms
- All charges clearly displayed before payment
- Payments processed through secure systems
- Refunds subject to our refund policy
- Pricing may vary by location and time

### Service Availability
- Services subject to station availability
- We don't guarantee uninterrupted service
- Maintenance may temporarily affect availability
- Force majeure events may impact service

## Station Owner Terms

### Partnership Requirements
- Valid business registration required
- Compliance with electrical and safety standards
- Insurance coverage for station operations
- Agreement to network standards and protocols

### Revenue Sharing
- Revenue sharing terms specified in separate agreement
- Payments processed monthly
- Accurate reporting required
- Tax responsibilities as per local law

## Prohibited Uses

### You May Not
- Use services for illegal activities
- Damage or tamper with charging equipment
- Share account credentials with others
- Attempt to bypass payment systems
- Interfere with other users' access

### Consequences
- Account suspension or termination
- Legal action for damages
- Reporting to law enforcement
- Recovery of costs and fees

## Intellectual Property

### Our Rights
- MengedMate trademarks and copyrights protected
- App and platform technology proprietary
- User-generated content license granted to us
- Respect for third-party intellectual property

### Your Rights
- License to use our services as intended
- Ownership of your personal information
- Right to feedback and suggestions
- Fair use of our public information

## Limitation of Liability

### Service Limitations
- Services provided "as is" without warranties
- We're not liable for charging station malfunctions
- Third-party services beyond our control
- User responsible for vehicle compatibility

### Damage Limitations
- Liability limited to amount paid for services
- No liability for indirect or consequential damages
- Force majeure events exclude liability
- Local law may provide additional protections

## Privacy and Data

### Data Collection
- Privacy Policy governs data practices
- Consent required for data processing
- Right to access and control your data
- Secure data handling and storage

### Communication
- Service-related communications permitted
- Marketing communications with consent
- Important updates may be sent to all users
- Opt-out options available

## Dispute Resolution

### Ethiopian Law
- These Terms governed by Ethiopian law
- Disputes resolved in Ethiopian courts
- Good faith negotiation encouraged first
- Arbitration may be available for certain disputes

### Complaint Process
- Contact customer support first
- Escalation procedures available
- Regulatory complaints permitted
- Legal action as last resort

## Service Changes

### Modifications
- We may update services and features
- Terms may be modified with notice
- Continued use constitutes acceptance
- Significant changes communicated clearly

### Service Termination
- Either party may terminate with notice
- Outstanding obligations survive termination
- Data deletion upon account closure
- Refunds processed per our policy

## Contact Information

### Customer Support
- Email: support@mengedmate.com
- Phone: +251-911-123-456
- Hours: 24/7 for emergencies, business hours for general support
- Website: www.mengedmate.com

### Legal Notices
- Email: legal@mengedmate.com
- Address: Addis Ababa, Ethiopia

## Miscellaneous

### Entire Agreement
These Terms, Privacy Policy, and service agreements constitute the complete agreement between us.

### Severability
If any provision is invalid, the remainder remains in effect.

### Assignment
We may assign these Terms; you may not without our consent.

Thank you for choosing MengedMate for your electric vehicle charging needs!
        """

        # Create or update About content
        about, created = AppContent.objects.get_or_create(
            content_type='about',
            defaults={
                'title': 'About MengedMate',
                'content': about_content.strip(),
                'version': '1.0',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created About MengedMate content'))
        else:
            self.stdout.write(self.style.WARNING('About MengedMate content already exists'))

        # Create or update Privacy Policy
        privacy, created = AppContent.objects.get_or_create(
            content_type='privacy_policy',
            defaults={
                'title': 'Privacy Policy',
                'content': privacy_policy_content.strip(),
                'version': '1.0',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Privacy Policy content'))
        else:
            self.stdout.write(self.style.WARNING('Privacy Policy content already exists'))

        # Create or update Terms of Service
        terms, created = AppContent.objects.get_or_create(
            content_type='terms_of_service',
            defaults={
                'title': 'Terms of Service',
                'content': terms_of_service_content.strip(),
                'version': '1.0',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Terms of Service content'))
        else:
            self.stdout.write(self.style.WARNING('Terms of Service content already exists'))

        self.stdout.write(self.style.SUCCESS('App content population completed!'))
