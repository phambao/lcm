from rest_framework import status
from django.urls import reverse

from .test_base import BaseTest
from ..models import Catalog


class CatalogTests(BaseTest):

    def setUp(self):
        """Create catalogs"""
        self.api_url = reverse('catalogs')

    def test_get_descendant_and_ancestor_catalog(self):
        """Test create catalogs"""
        num_children = 7
        parent = None
        list_catalog_id = []
        for i in range(num_children):
            data = {
                "name": f"Catalog {i}",
                "parent": parent,
                "sequence": 0,
                "cost_table": None,
                "icon": None,
                "is_ancestor": False,
                "level": None,
                "data_points": '',
                "children": []
            }
            response = self.client.post(
                self.api_url,
                data,
                format='json',
                HTTP_AUTHORIZATION=self.token)
            parent = response.data['id']
            list_catalog_id.append(parent)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        catalog = Catalog.objects.get(id=list_catalog_id[0])
        self.assertEqual(len(catalog.get_all_descendant()), num_children-1)

    def test_add_multiple_level_catalog(self):
        data = {
            "catalog": {
                "name": "example"
            },
            "levels": ['level 1', 'level 2', 'level 3']
        }
        response = self.client.post(
            reverse('add-multiple-level'),
            data,
            format='json',
            HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        catalog = Catalog.objects.get(pk=response.data['catalog']['id'])
        self.assertEqual(len(catalog.get_ordered_levels()), len(data['levels']))
