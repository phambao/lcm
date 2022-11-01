from django.db import models


class Country(models.Model):
    """Country information"""
    class Meta:
        db_table = 'country'

    name = models.CharField(max_length=128)
    iso2 = models.CharField(max_length=2)
    phone_code = models.CharField(max_length=16)
    currency = models.CharField(max_length=16)
    currency_name = models.CharField(max_length=128)
    currency_symbol = models.CharField(max_length=16)
    region = models.CharField(max_length=128)
    subregion = models.CharField(max_length=128)

    def __str__(self):
        return self.name
    

class State(models.Model):
    """State information"""
    class Meta:
        db_table = 'state'

    name = models.CharField(max_length=128)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='state')

    def __str__(self):
        return self.name
    
    
class City(models.Model):
    """City information"""
    class Meta:
        db_table = 'city'

    name = models.CharField(max_length=128)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='city')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='city')

    def __str__(self):
        return self.name


class ZipCode(models.Model):
    """Zipcode information"""
    class Meta:
        db_table = 'zipcode'

    zipcode = models.CharField(max_length=16, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='zipcode')
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='zipcode')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='zipcode')
    
    def __str__(self):
        return self.zipcode
