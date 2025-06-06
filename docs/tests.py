from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from unittest.mock import patch, mock_open
import os

User = get_user_model()


class DocumentationViewTests(TestCase):
    """Test cases for Documentation views"""

    def setUp(self):
        self.client = Client()

    def test_user_documentation_view(self):
        """Test user documentation view"""
        url = reverse('user-guide')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'evmeri User Guide')
        self.assertContains(response, 'Table of Contents')

    def test_technical_documentation_view(self):
        """Test technical documentation view"""
        url = reverse('technical-docs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'evmeri Technical Documentation')
        self.assertContains(response, 'Table of Contents')

    def test_documentation_template_rendering(self):
        """Test that documentation templates render correctly"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check that the response contains expected HTML structure
        self.assertContains(response, '<html>')
        self.assertContains(response, '<head>')
        self.assertContains(response, '<body>')
        self.assertContains(response, '</html>')

    def test_documentation_css_styling(self):
        """Test that documentation includes CSS styling"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for CSS styles
        self.assertContains(response, '<style>')
        self.assertContains(response, 'font-family')
        self.assertContains(response, 'color')

    def test_documentation_navigation_links(self):
        """Test that documentation includes navigation links"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for table of contents links
        self.assertContains(response, 'href="#welcome-to-evmeri"')
        self.assertContains(response, 'href="#getting-started"')
        self.assertContains(response, 'href="#account-management"')

    def test_technical_documentation_sections(self):
        """Test that technical documentation includes all required sections"""
        url = reverse('technical-docs')
        response = self.client.get(url)

        # Check for key technical sections
        self.assertContains(response, 'Overview')
        self.assertContains(response, 'Architecture')
        self.assertContains(response, 'Installation')
        self.assertContains(response, 'API Documentation')
        self.assertContains(response, 'Testing')

    def test_user_documentation_sections(self):
        """Test that user documentation includes all required sections"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for key user sections
        self.assertContains(response, 'Welcome to evmeri')
        self.assertContains(response, 'Getting Started')
        self.assertContains(response, 'Finding Charging Stations')
        self.assertContains(response, 'Payment & Billing')
        self.assertContains(response, 'Mobile App Features')

    def test_documentation_responsive_design(self):
        """Test that documentation includes responsive design elements"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for responsive design CSS
        self.assertContains(response, 'max-width')
        self.assertContains(response, 'margin: 0 auto')

    def test_documentation_accessibility(self):
        """Test that documentation includes accessibility features"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for accessibility features
        self.assertContains(response, 'id=')  # Section IDs for navigation
        self.assertContains(response, '<h1>')  # Proper heading structure
        self.assertContains(response, '<h2>')
        self.assertContains(response, '<h3>')

    def test_documentation_code_examples(self):
        """Test that technical documentation includes code examples"""
        url = reverse('technical-docs')
        response = self.client.get(url)

        # Check for code blocks
        self.assertContains(response, '<pre>')
        self.assertContains(response, '<code>')

    def test_documentation_file_existence(self):
        """Test that documentation HTML files exist"""
        from django.conf import settings

        # Check user documentation file
        user_doc_path = os.path.join(settings.BASE_DIR, 'docs', 'static', 'docs', 'user_documentation.html')
        self.assertTrue(os.path.exists(user_doc_path), "User documentation HTML file should exist")

        # Check technical documentation file
        tech_doc_path = os.path.join(settings.BASE_DIR, 'docs', 'static', 'docs', 'technical_documentation.html')
        self.assertTrue(os.path.exists(tech_doc_path), "Technical documentation HTML file should exist")

    def test_documentation_content_type(self):
        """Test that documentation returns correct content type"""
        url = reverse('user-guide')
        response = self.client.get(url)

        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_documentation_caching_headers(self):
        """Test that documentation includes appropriate caching headers"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Documentation should be cacheable for performance
        self.assertIn('Cache-Control', response)

    def test_documentation_mobile_viewport(self):
        """Test that documentation includes mobile viewport meta tag"""
        url = reverse('user-guide')
        response = self.client.get(url)

        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, 'width=device-width')

    def test_documentation_search_functionality(self):
        """Test that documentation includes search-friendly structure"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for search-friendly elements
        self.assertContains(response, 'id="')  # IDs for deep linking
        self.assertContains(response, 'Table of Contents')  # Navigation structure

    def test_documentation_print_styles(self):
        """Test that documentation includes print-friendly styles"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for print considerations in CSS
        content = response.content.decode('utf-8')
        # Documentation should be readable when printed
        self.assertIn('font-family', content)
        self.assertIn('line-height', content)


class DocumentationURLTests(TestCase):
    """Test cases for Documentation URL patterns"""

    def test_user_guide_url_resolution(self):
        """Test that user guide URL resolves correctly"""
        url = reverse('user-guide')
        self.assertEqual(url, '/docs/user-guide/')

    def test_technical_docs_url_resolution(self):
        """Test that technical docs URL resolves correctly"""
        url = reverse('technical-docs')
        self.assertEqual(url, '/docs/technical/')

    def test_documentation_url_accessibility(self):
        """Test that documentation URLs are accessible"""
        # Test user guide
        response = self.client.get('/docs/user-guide/')
        self.assertEqual(response.status_code, 200)

        # Test technical docs
        response = self.client.get('/docs/technical/')
        self.assertEqual(response.status_code, 200)

    def test_documentation_url_redirects(self):
        """Test that documentation URLs handle redirects properly"""
        # Test trailing slash handling
        response = self.client.get('/docs/user-guide')
        # Should either work or redirect to version with trailing slash
        self.assertIn(response.status_code, [200, 301, 302])


class DocumentationIntegrationTests(TestCase):
    """Integration tests for Documentation functionality"""

    def test_documentation_full_page_load(self):
        """Test that documentation pages load completely"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check that response is complete
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Check that HTML is well-formed
        self.assertTrue(content.count('<html>') == 1)
        self.assertTrue(content.count('</html>') == 1)
        self.assertTrue(content.count('<body>') == 1)
        self.assertTrue(content.count('</body>') == 1)

    def test_documentation_cross_references(self):
        """Test that documentation includes proper cross-references"""
        url = reverse('user-guide')
        response = self.client.get(url)

        # Check for internal links
        self.assertContains(response, 'href="#')

        # Check for section references
        content = response.content.decode('utf-8')
        # Should have multiple internal navigation links
        internal_links = content.count('href="#')
        self.assertGreater(internal_links, 10)

    def test_documentation_performance(self):
        """Test that documentation loads efficiently"""
        import time

        start_time = time.time()
        url = reverse('user-guide')
        response = self.client.get(url)
        end_time = time.time()

        # Documentation should load quickly (under 1 second)
        load_time = end_time - start_time
        self.assertLess(load_time, 1.0, "Documentation should load in under 1 second")
        self.assertEqual(response.status_code, 200)
