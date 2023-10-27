from rest_framework import status

from sales.tests.test_base import BaseTest


class CompanyTests(BaseTest):
    def setUp(self):
        """Create a company"""
        self.company_data = {
            "logo": "string",
            "company_name": "string",
            "address": "string",
            # "city": 1,
            # "state": 1,
            "zip_code": "string",
            "tax": "string",
            "size": 2,
            "business_phone": "string",
            "cell_phone": "string",
            "fax": "string",
            "email": "user@example.com",
            "cell_mail": "string",
            "user_create": self.user_id,
            "user_update": self.user_id
        }
        self.company = self.client.post(
            f'/api/base/company/',
            self.company_data, format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(self.company.status_code, status.HTTP_201_CREATED)
        self.company_id = self.company.data['id']

    def test_delete_company(self):
        """Test delete company"""
        res_delete = self.client.delete(
            f'/api/base/company/{self.company_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if company is deleted
        res_data = self.client.get(
            f'/api/base/company/{self.company_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_data.status_code, status.HTTP_404_NOT_FOUND)
