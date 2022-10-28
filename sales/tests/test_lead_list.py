from rest_framework import status

from .test_base import BaseTest
from ..models import lead_list
from api.models import User

class LeadDetailTests(BaseTest):

    def setUp(self):
        self.client.post('/api/sales/contact-types/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.client.post('/api/sales/lead-list/project-types/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.client.post('/api/sales/lead-list/activity/tags/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.client.post('/api/sales/lead-list/activity/phase/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)

    def test_lead_detail_create(self):
        response = self.client.post('/api/sales/lead-list/leads/', {
            "activities": [],
            "contacts": [],
            "photos": [],
            "city": {},
            "state": {},
            "country": {},
            "project_types": [
                {
                    "id": 1,
                    "name": "test"
                }
            ],
            "lead_title": "test",
            "salesperson": [{"id": 3}],
            "projected_sale_date": "2022-01-01T00:00:00Z",
            "zip_code": "{}",
            "status": "open",
            "proposal_status": "approved",
            "notes": "",
            "confidence": 1,
            "estimate_revenue_from": "1.00",
            "estimate_revenue_to": "1.00",
            "source": "",
            "tags": ""
        }, HTTP_AUTHORIZATION=self.token, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

