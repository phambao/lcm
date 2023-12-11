from django.urls import reverse
from rest_framework import status

from .test_base import BaseTest


class CatalogTests(BaseTest):

    def setUp(self):
        """Create proposal"""
        self.api_url = reverse('list-change-order')

    def test_proposal(self):
        data = {
            "changed_items": [],
            "existing_estimates": [],
            "groups": [],
            "flat_rate_groups": [],
            "name": "CREATE CHANGE ORDER",
            "approval_deadline": "2023-12-11T07:26:45Z"
        }
        # Create
        response = self.client.post(
            self.api_url,
            data,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        id = response.data['id']

        # Update
        data['name'] = 'new name'
        response = self.client.put(
            reverse('detail-change-order', args=[response.data['id']]),
            data,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.data['name'], data['name'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete
        response = self.client.delete(
            reverse('detail-change-order', args=[response.data['id']]),
            '',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(
            reverse('detail-change-order', args=[id]),
            None,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
