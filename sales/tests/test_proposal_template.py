from rest_framework import status

from .test_base import BaseTest


class ProposalTemplateTests(BaseTest):
    def setUp(self):
        """Create a proposal template"""
        self.api_url = '/api/sales/proposal'
        self.template_data = {
            "name": "day la test",
            "proposal_template_element": [],
            "config": {
                "type": "abc",
                "value": 'example'
            }
        }
        proposal_template = self.client.post(
            f'{self.api_url}/template/',
            self.template_data, format='json',
            HTTP_AUTHORIZATION=self.token)

        self.proposal_template_id = proposal_template.data['id']

        data = {
            "name": "day là template 1",
            "proposal_formatting_template": {
                "name": "string",
                "proposal_template_element": [

                ],
                "config": {
                    "display_order": 2147483647,
                    "proposal_widget_element": [
                        {
                            "id": 0,
                            "proposal_element": 0,
                            "type_widget": "string",
                            "title": "string",
                            "display_order": 2147483647,
                            "data_widget": {}
                        }
                    ],
                    "title": "string"
                }
            },
            "choose_update_template": False,
            "proposal_template": self.proposal_template_id
        }
        proposal_formatting_template = self.client.post(
            f'{self.api_url}/formatting-template/',
            data, format='json',
            HTTP_AUTHORIZATION=self.token)
        self.proposal_formatting_template_id = proposal_formatting_template.data['id']

    def test_update_proposal_formatting_template(self):
        """Test delete proposal_formatting_template"""
        res_delete = self.client.delete(
            f'{self.api_url}/formatting-template/{self.proposal_formatting_template_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if proposal template is deleted
        res_deleted = self.client.get(
            f'{self.api_url}/formatting-template/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)

    def test_delete_proposal_formatting_template(self):
        """Test delete proposal_formatting_template"""
        res_delete = self.client.delete(
            f'{self.api_url}/formatting-template/{self.proposal_formatting_template_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if proposal template is deleted
        res_deleted = self.client.get(
            f'{self.api_url}/formatting-template/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)

    def test_delete_proposal_template(self):
        """Test delete proposal template"""
        res_delete = self.client.delete(
            f'{self.api_url}/template/{self.proposal_template_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if proposal template is deleted
        res_deleted = self.client.get(
            f'{self.api_url}/template/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_deleted.data['count'], 0)
