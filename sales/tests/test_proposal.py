from django.urls import reverse
from rest_framework import status

from .test_base import BaseTest


class CatalogTests(BaseTest):

    def setUp(self):
        """Create proposal"""
        self.api_url = reverse('list-proposal')

    def no_test_proposal(self):
        data = {
            "writing_groups": [],
            "name": "Proposal Writing - General",
            "budget": "",
            "total_project_price": 0,
            "total_project_cost": 0,
            "gross_profit": 0,
            "gross_profit_percent": 0,
            "avg_markup": 0,
            "cost_breakdown": [],
            "add_on_total_project_price": 0,
            "add_on_total_project_cost": 0,
            "add_on_gross_profit": 0,
            "add_on_gross_profit_percent": 0,
            "add_on_avg_markup": 0,
            "add_on_cost_breakdown": [],
            "additional_cost_total_project_price": 0,
            "additional_cost_total_project_cost": 0,
            "additional_cost_gross_profit": 0,
            "additional_cost_gross_profit_percent": 0,
            "additional_cost_avg_markup": 0,
            "additional_cost_breakdown": [],
            "estimated_start_date": "2023-06-07T08:22:33.108437Z",
            "estimated_end_date": "2023-06-07T08:22:33.108437Z",
            "additional_information": [],
            "lead": None
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
            reverse('detail-proposal', args=[response.data['id']]),
            data,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.data['name'], data['name'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete
        response = self.client.delete(
            reverse('detail-proposal', args=[response.data['id']]),
            '',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(
            reverse('detail-proposal', args=[id]),
            None,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
