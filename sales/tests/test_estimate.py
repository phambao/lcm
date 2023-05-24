from django.urls import reverse
from rest_framework import status

from .test_base import BaseTest


class DataEntryTest(BaseTest):
    def setUp(self) -> None:
        self.data_entry_url = reverse('sales.estimate.data-entry')

    def test_create_data_entry(self):
        data = {
            'name': 'data entry'
        }
        response = self.client.post(self.data_entry_url, data, format='json', HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data_entries = self.client.get(self.data_entry_url, HTTP_AUTHORIZATION=self.token)
        self.data_entry_detail_url = reverse('sales.estimate.data-entry.detail',
                                             kwargs={'pk': data_entries.json().get('results')[0].get('id')})
        put_data = {
            'name': 'update'
        }
        response = self.client.put(self.data_entry_detail_url, put_data, forma='json', HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('name'), put_data.get('name'))

        response = self.client.delete(self.data_entry_detail_url, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
