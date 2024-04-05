from rest_framework import status

from .test_base import BaseTest


class LeadScheduleTests(BaseTest):
    def setUp(self):
        """Create a lead"""
        self.todo_id = None
        self.daily_log = None
        self.event_id = None
        self.api_url = '/api/sales/schedule'
        self.lead_data = {
            'lead_title': 'Test',
            'activities': [],
            'contacts': [],
            'photos': [],
            'city': '',
            'state': '',
            'country': '',
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

        """Create a to_do"""

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
        self.todo_id = response.data['id']

        """Create a daily log"""

        schedule_daily_log_data = {
            "date": "2023-02-28T03:02:54.193Z",
            "tags": [

            ],
            "to_dos": [
                {
                    "id": self.todo_id,
                    "name": "string"
                }
            ],
            "note": "string",
            "lead_list": self.lead_id,
            "internal_user_share": True,
            "internal_user_notify": True,
            "sub_member_share": True,
            "sub_member_notify": True,
            "owner_share": True,
            "owner_notify": True,
            "private_share": True,
            "private_notify": True,
            "custom_field": [
            ],
            "title": "string",
            "color": "#AFFFF1",
        }
        response = self.client.post(
            f'{self.api_url}/daily-logs/',
            schedule_daily_log_data,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.daily_log = response.data['id']

        """Create a event"""

        schedule_event_data = {
            "lead_list": self.lead_id,
            "event_title": "string",
            "assigned_user": [
                {
                    "id": self.user_id,
                    "email": "user@example.com",
                    "username": "string",
                    "last_name": "string",
                    "first_name": "string"
                }
            ],
            "reminder": 1,
            "start_day": "2023-02-28T03:59:33.683Z",
            "end_day": "2023-02-28T03:59:33.683Z",
            "due_days": 2,
            "time": 2,
            "viewing": [
                {
                    "id": self.user_id,
                    "email": "user@example.com",
                    "username": "string",
                    "last_name": "string",
                    "first_name": "string"
                }
            ],
            "notes": "string",
            "internal_notes": "string",
            "sub_notes": "string",
            "owner_notes": "string",
            "links": [

            ],
            "start_hour": "2023-02-28T03:59:33.683Z",
            "end_hour": "2023-02-28T03:59:33.683Z",
            "is_before": True,
            "is_after": True,
            "is_hourly": True,
            "type": "finish_to_start",
            "lag_day": 1,
            "link_to_outside_calendar": True,
            "tags": [
            ],
            "phase_label": "string",
            "phase_display_order": 1,
            "phase_color": "string",
            "color": "string",
            "shift": [
            ]
        }
        # response = self.client.post(
        #     f'{self.api_url}/schedule-event/',
        #     schedule_event_data,
        #     format='json',
        #     HTTP_AUTHORIZATION=self.token)
        #
        # self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # self.event_id = response.data['id']

    def test_delete_todo(self):
        """Test delete multiple to_do"""
        res_delete = self.client.delete(
            f'{self.api_url}/todo/delete/',
            [self.todo_id],
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if leads is deleted
        res_deleted = self.client.get(
            f'{self.api_url}/todo/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)

    def test_delete_daily_log(self):
        """Test delete multiple daily log"""
        res_delete = self.client.delete(
            f'{self.api_url}/daily-logs/delete/',
            [self.daily_log],
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if leads is deleted
        res_deleted = self.client.get(
            f'{self.api_url}/daily-logs/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)

    # def test_delete_event(self):
    #     """Test delete multiple event"""
    #     res_delete = self.client.delete(
    #         f'{self.api_url}/schedule-events/delete/',
    #         [self.event_id],
    #         format='json',
    #         HTTP_AUTHORIZATION=self.token)
    #     self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
    #
    #     # Check if leads is deleted
    #     res_deleted = self.client.get(
    #         f'{self.api_url}/schedule-event/',
    #         format='json',
    #         HTTP_AUTHORIZATION=self.token)
    #     self.assertEqual(res_deleted.data['count'], 0)
