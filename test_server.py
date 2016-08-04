import unittest
import server

class homepageTestCase(unittest.TestCase):

    def setUp(self):
        """Create a browser for testing."""

        self.client = server.app.test_client()
        server.app.config['TESTING'] = True


    def test_homepage_links(self):
        """Checks to make sure there are specific links on the homepage."""

        result = self.client.get('/')
        self.assertIn('/movies', result.data)
        self.assertIn('/users', result.data)


    def test_homepage_navbar(self):
        """Test that navbar appears on homepage."""

        result = self.client.get('/')
        self.assertIn('<div class="navbar-header">', result.data)


if __name__ == '__main__':
    unittest.main()
