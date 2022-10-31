from rest_framework import status

from .test_base import BaseTest
from ..models import lead_list
from base.models import country_state_city
from api.models import User


class LeadDetailTests(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = country_state_city.Country.objects.create(name='USA')
        cls.state = country_state_city.State.objects.create(name='California', country=cls.country)
        cls.city = country_state_city.City.objects.create(name='Los Angeles', state=cls.state, country=cls.country)
        cls.tag_lead = lead_list.TagLead.objects.create(name='Test')
        cls.contact_types = lead_list.ContactTypeName.objects.create(name='Test')
        cls.project_types = lead_list.ProjectType.objects.create(name='Test')
        cls.tag_activity = lead_list.TagActivity.objects.create(name='Test')
        cls.phase_activity = lead_list.PhaseActivity.objects.create(name='Test')

    def test_lead_detail_create(self):
        response = self.client.post(
            '/api/sales/lead-list/leads/', 
            {
                'lead_title': 'Test',
                'activities': [],
                'contacts': [],
                'photos': [],
                'city': {},
                'state': {},
                'country': {},
                'project_types': [
                    {
                        'id': self.project_types.id
                    }
                ],
                
                'salesperson': [
                    {
                        'id': self.user_id
                    }
                ],
                'projected_sale_date': '2022-01-01T00:00:00Z',
                'zip_code': '',
                'status': 'open',
                'proposal_status': 'approved',
                'notes': '',
                'confidence': 1,
                'estimate_revenue_from': '1.00',
                'estimate_revenue_to': '1.00',
                'source': '',
                'tags': [
                    {
                        'id': self.tag_lead.id
                    }
                ]

            },
            format='json',
            HTTP_AUTHORIZATION=self.token)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_lead_detail_get(self):
        response = self.client.get(
            '/api/sales/lead-list/leads/', HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
