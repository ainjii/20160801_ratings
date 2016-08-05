import unittest
import server
import tempfile
import os


class homepageTestCase(unittest.TestCase):
    def setUp(self):
        """Create a browser for testing."""
        self.db, server.app.config['DATABASE'] = tempfile.mkstemp()
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        with server.app.app_context():
            server.connect_to_db(server.app)


    def tearDown(self):
        os.close(self.db)
        os.unlink(server.app.config['DATABASE'])


    def test_homepage_links(self):
        """Checks to make sure there are specific links on the homepage."""

        result = self.client.get('/')
        self.assertIn('/movies', result.data)
        self.assertIn('/users', result.data)


    def test_homepage_navbar(self):
        """Test that navbar appears on homepage."""

        result = self.client.get('/')
        self.assertIn('<div class="navbar-header">', result.data)


class loginTestCase(unittest.TestCase):
    def setUp(self):
        """Create a browser for testing."""
        self.db, server.app.config['DATABASE'] = tempfile.mkstemp()
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        with server.app.app_context():
            server.connect_to_db(server.app)


    def tearDown(self):
        os.close(self.db)
        os.unlink(server.app.config['DATABASE'])


    def login(self, username, password):
        return self.client.post('/process_registration', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)


    def logout(self):
        return self.client.get('/logout', follow_redirects=True)


    def test_login_logout(self):
        rv = self.login('user', 'pass')
        assert 'You were successfully logged in.' in rv.data
        rv = self.logout()
        assert 'You have been logged out.' in rv.data
        rv = self.login('user', 'defaultx')
        assert 'Incorrect password.' in rv.data


class movieTestCase(unittest.TestCase):
    def setUp(self):
        """Create a browser for testing."""
        self.db, server.app.config['DATABASE'] = tempfile.mkstemp()
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        with server.app.app_context():
            server.connect_to_db(server.app)


    def tearDown(self):
        os.close(self.db)
        os.unlink(server.app.config['DATABASE'])


if __name__ == '__main__':
    unittest.main()
