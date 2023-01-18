from django.test import Client
from rest_framework.test import APITestCase

from api.models import User


class BaseTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = User.objects.create_user(username='tester', email='test@example.com', last_name='test',
                                        first_name='test')
        user.set_password('1')
        user.save()
        cls.response = Client().post('/api/login',
                                     {'username': 'tester', 'password': '1', 'email': 'test@example.com'},
                                     format='json')
        cls.user_id = cls.response.data['user']['id']
        cls.token = 'Token {}'.format(cls.response.data['token'])
