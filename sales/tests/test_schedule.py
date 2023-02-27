from rest_framework import status

from .test_base import BaseTest


class LeadScheduleTests(BaseTest):
    def setUp(self):
        """Create a lead"""
        self.api_url = '/api/sales/schedule'
        self.lead_data = {
            'lead_title': 'Test',
            'activities': [],
            'contacts': [],
            'photos': [],
            'city': {},
            'state': {},
            'country': {},
            'project_types': [],
            'salesperson': [{"id": self.user_id}],
            'projected_sale_date': '2022-01-01T00:00:00Z',
            'zip_code': '',
            'status': 'open',
            'proposal_status': 'approved',
            'notes': '',
            'confidence': 1,
            'estimate_revenue_from': '1.00',
            'estimate_revenue_to': '1.00',
            'sources': [],
            'tags': []
        }
        self.lead = self.client.post(
            f'/api/sales/lead-list/leads/',
            self.lead_data, format='json',
            HTTP_AUTHORIZATION=self.token)
        self.lead_id = self.lead.data['id']

    def test_create_todo(self):
        """Test create schedule to_do"""
        schedule_todo_data = {
            "assigned_to": [
                {
                    "id": self.user_id,
                    "email": "user@example.com",
                    "username": "string",
                    "last_name": "string",
                    "first_name": "string"
                }
            ],
            "tags": [

            ],
            "title": "day la test todo",
            "priority": "high",
            "due_date": "2023-02-27T06:52:33.138Z",
            "time_hour": "2023-02-27T06:52:33.138Z",
            "is_complete": True,
            "sync_due_date": "2023-02-27T06:52:33.138Z",
            "reminder": 1,
            "notes": "day là note",
            "color": "#AFFFF1",
            "lead_list": self.lead_id

        }
        response = self.client.post(
            f'{self.api_url}/todo/',
            schedule_todo_data,
            format='json',
            HTTP_AUTHORIZATION=self.token)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
