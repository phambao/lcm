from rest_framework import status

from sales.tests.test_base import BaseTest
import stripe


class CompanyTests(BaseTest):
    def setUp(self):
        stripe.api_key = 'sk_test_51NN9dpE4OZckNkJ54bksNl7qbfONbBeJdvsY1XGSrXBVllwVhMani8Q3rNTy5WgVO1v455P6XXyLQdDcmiATEQrF00NE3sX2EE'
        """Create a company"""
        self.company_data = {
            "logo": "string",
            "company_name": "day la de chay test a",
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
        self.person_information = None
        self.trades_id = None

        data_person_information = {
            "fullname": "string",
            "phone_number": "string",
            "email": "user@example.com",
            "address": "string",
            "company": self.company_id,
            "first_name": "string",
            "last_name": "string",
            "nick_name": "string"
        }
        res_create = self.client.post(
            f'/api/base/personal-information/',
            data_person_information,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.person_information = res_create.data['id']
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        data_trades = {
            "name": "abc",
            "is_show": True
        }
        res_create_trades = self.client.post(
            f'/api/base/company/trades/',
            data_trades,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.trades_id = res_create_trades.data['id']
        self.assertEqual(res_create_trades.status_code, status.HTTP_201_CREATED)

        data_division = {
            "name": "abc",
            "company": self.company_id
        }
        res_create_division = self.client.post(
            f'/api/base/company/division/',
            data_division,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.division_id = res_create_division.data['id']
        self.assertEqual(res_create_division.status_code, status.HTTP_201_CREATED)

    def test_update_company(self):
        """Test delete company"""
        data_company = {
            "logo": "string 1",
            "company_name": "company update",
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
        res_delete = self.client.put(
            f'/api/base/company/{self.company_id}/',
            data_company,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_200_OK)


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

    def test_update_person_information(self):
        """Test update person information"""
        data_update = {
            "fullname": "string",
            "phone_number": "string",
            "email": "user@example.com",
            "address": "string",
            "company": self.company_id,
            "first_name": "string",
            "last_name": "string",
            "nick_name": "string"
        }
        res_delete = self.client.put(
            f'/api/base/personal-information/{self.person_information}/',
            data_update,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_200_OK)

    def test_delete_person_information(self):
        """Test delete person information"""
        res_delete = self.client.delete(
            f'/api/base/personal-information/{self.person_information}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)

        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        # Check if person information is deleted
        res_data = self.client.get(
            f'/api/base/personal-information/{self.person_information}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_data.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_trades(self):
        """Test update trades"""
        data_update = {
            "name": "day la thay doi",
            "is_show": True
        }
        res_delete = self.client.put(
            f'/api/base/company/trades/{self.trades_id}/',
            data_update,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_delete.status_code, status.HTTP_200_OK)

    def test_delete_trades(self):
        """Test delete trades"""
        res_delete = self.client.delete(
            f'/api/base/company/trades/{self.trades_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)

        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        res_data = self.client.get(
            f'/api/base/company/trades/{self.trades_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_data.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_division(self):
        """Test update division"""
        data_update = {
            "name": "day la thay doi",
            "company": self.company_id
        }
        res_update = self.client.put(
            f'/api/base/company/division/{self.division_id}/',
            data_update,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)

    def test_delete_division(self):
        """Test delete division"""
        res_delete = self.client.delete(
            f'/api/base/company/division/{self.division_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)

        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

        res_data = self.client.get(
            f'/api/base/company/division/{self.division_id}/',
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(res_data.status_code, status.HTTP_404_NOT_FOUND)