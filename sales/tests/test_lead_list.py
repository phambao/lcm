from rest_framework import status

from .test_base import BaseTest
from ..models import lead_list
from api.models import User


class LeadDetailTests(BaseTest):

    def setUp(self):
        res_contact_types = self.client.post('/api/sales/contact-types/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.contact_type_id = res_contact_types.data['id']
        res_project_types = self.client.post('/api/sales/lead-list/project-types/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.project_type_id = res_project_types.data['id']
        res_tag_activity = self.client.post('/api/sales/lead-list/activity/tags/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.tag_activity_id = res_tag_activity.data['id']
        res_phase_activity = self.client.post('/api/sales/lead-list/activity/phase/',
                         {'name': 'test'}, HTTP_AUTHORIZATION=self.token)
        self.phase_activity_id = res_phase_activity.data['id']

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
                    "id": self.project_type_id
                }
            ],
            "lead_title": "Test",
            "salesperson": [{"id": self.user_id}],
            "projected_sale_date": "2022-01-01T00:00:00Z",
            "zip_code": "",
            "status": "open",
            "proposal_status": "approved",
            "notes": "",
            "confidence": 1,
            "estimate_revenue_from": "1.00",
            "estimate_revenue_to": "1.00",
            "source": "",
            "tags": []
        }, HTTP_AUTHORIZATION=self.token, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
