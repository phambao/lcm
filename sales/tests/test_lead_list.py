from rest_framework import status

from .test_base import BaseTest


class LeadDetailTests(BaseTest):

    def setUp(self):
        """Create a lead"""
        self.api_url = '/api/sales/lead-list'
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
            f'{self.api_url}/leads/',
            self.lead_data, format='json',
            HTTP_AUTHORIZATION=self.token)
        self.lead_id = self.lead.data['id']

    def test_create_lead(self):
        """Test create lead"""
        response = self.client.post(
            f'{self.api_url}/leads/',
            self.lead_data,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_leads(self):
        """Test delete multiple leads"""
        res_delete = self.client.delete(
            f'{self.api_url}/leads/delete/',
            [self.lead_id],
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if leads is deleted
        res_deleted = self.client.get(
            f'{self.api_url}/leads/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)

    def test_with_activities_in_lead(self):
        """Test for activities in lead"""
        activities = [
            {
                "title": "Test 1",
                "is_completed": False,
                "phase": {},
                "tags": [],
                "status": "none",
                "start_date": "2021-01-01T00:00:00Z",
                "end_date": "2021-01-01T00:00:00Z",
                "assigned_to": [],
                "attendees": []
            },
            {
                "title": "Test 2",
                "is_completed": False,
                "phase": {},
                "tags": [],
                "status": "none",
                "start_date": "2021-01-01T00:00:00Z",
                "end_date": "2021-01-01T00:00:00Z",
                "assigned_to": [],
                "attendees": []
            }
        ]
        # Create activities
        ids = []
        for activity in activities:
            res_post = self.client.post(
                f'{self.api_url}/leads/{self.lead_id}/activities/',
                activity,
                format='json',
                HTTP_AUTHORIZATION=self.token)
            ids.append(res_post.data['id'])
            self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)

        # Update activity
        res_put = self.client.put(
            f'{self.api_url}/leads/{self.lead_id}/activities/{ids[0]}/',
            {
                "title": "Test 1 Updated",
                "is_completed": True,
                "phase": {},
                "tags": [],
                "status": "none",
                "start_date": "2022-01-01T00:00:00Z",
                "end_date": "2022-01-01T00:00:00Z",
                "assigned_to": [],
                "attendees": []
            },
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)

        # Delete multiple activities
        res_delete = self.client.delete(
            f'{self.api_url}/leads/{self.lead_id}/activities/delete/',
            ids,
            format='json',
            HTTP_AUTHORIZATION=self.token
        )
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if all activities are deleted
        res_get = self.client.get(
            f'{self.api_url}/leads/{self.lead_id}/activities/',
            format='json',
            HTTP_AUTHORIZATION=self.token
        )
        self.assertEqual(res_get.data['count'], 0)

    def test_with_contacts_in_lead(self):
        """Test for contacts in lead"""
        contacts = [
            {
                'first_name': 'Tester',
                'last_name': '1',
                'email': 'test@test1.com',
                'gender': '',
                'street': '',
                'city': '',
                'state': '',
                'country': '',
                'zip_code': '',
                'image': '',
                'phone_contacts': [{
                    'phone_number': '1234',
                    'phone_type': 'mobile',
                    'text_message_received': '',
                    'mobile_phone_service_provider': ''
                }],
                'contact_types': [],
            },
            {
                'first_name': 'Tester',
                'last_name': '2',
                'email': 'test@test2.com',
                'gender': '',
                'street': '',
                'city': '',
                'state': '',
                'country': '',
                'zip_code': '',
                'image': '',
                'phone_contacts': [{
                    'phone_number': '2345',
                    'phone_type': 'mobile',
                    'text_message_received': '',
                    'mobile_phone_service_provider': ''
                }],
                'contact_types': [],
            }
        ]
        # Create contacts
        ids = []
        for contact in contacts:
            response = self.client.post(
                f'{self.api_url}/leads/{self.lead_id}/contacts/',
                contact,
                format='json',
                HTTP_AUTHORIZATION=self.token
            )
            ids.append(response.data['id'])
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Unlink multiple contacts in lead
        res_unlink = self.client.put(
            f'{self.api_url}/leads/{self.lead_id}/contacts/unlink/',
            ids,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_unlink.status_code, status.HTTP_200_OK)

        # Check if all contacts in lead are unlinked
        res_unlinked = self.client.get(
            f'{self.api_url}/leads/{self.lead_id}/contacts/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_unlinked.data['count'], 0)

        # Link multiple contacts in lead
        res_link = self.client.put(
            f'{self.api_url}/leads/{self.lead_id}/contacts/link/',
            ids,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_link.status_code, status.HTTP_200_OK)

        # Check if all contacts in lead are linked
        res_linked = self.client.get(
            f'{self.api_url}/leads/{self.lead_id}/contacts/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_linked.data['count'], len(contacts))

        # Delete multiple contacts
        res_delete = self.client.delete(
            '/api/sales/contacts/delete/',
            ids,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if all contacts are deleted
        res_deleted = self.client.get(
            '/api/sales/contacts/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)
