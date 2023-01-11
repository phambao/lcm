from rest_framework import status
from rest_framework.test import APITestCase

from api.models import User


class AuthTests(APITestCase):
    def setUp(self):
        User.objects.create_user(
            username='admin', password='admin', email='admin@admin.com')

    def test_auth(self):
        # register
        response = self.client.post('/api/register', {'username': 'test', 'password': 'test',
                                                      'email': 'test@test.com', 'first_name': 'test',
                                                      'last_name': 'test'}, format='json')
        # login
        response = self.client.post(
            '/api/login', {'email': 'admin@admin.com', 'password': 'admin', 'username': 'admin'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # get token
        token = response.data['token']
        # logout
        response = self.client.post(
            '/api/logoutall/', HTTP_AUTHORIZATION='Token {}'.format(token))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
