from tortoise import Tortoise, fields, run_async
from tortoise.models import Model



class Coin(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, description='Name of the cryptocurrency')
    price=fields.FloatField()
    # datetime = fields.DatetimeField(auto_now_add=True, description='Created datetime')
    
    coin_type = fields.ForeignKeyField('models.Coin_type', related_name='coins', null=True)

    class Meta:
        table = 'coin'
        table_description = 'This table contains a list of all the cryptocurrencies'

    def __str__(self):
        return self.name


class Coin_type(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, description='type name of the coin')
 
    class Meta:
        table = 'coin_type'
        table_description = 'This table contains a type list of the coins'

    def __str__(self):
        return self.name

