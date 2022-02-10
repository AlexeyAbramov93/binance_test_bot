from tortoise import Tortoise, fields, run_async
from tortoise.models import Model



class Candle(Model):
    id = fields.IntField(pk=True)

    timestamp=fields.CharField(max_length=30)
    balance=fields.FloatField()
    signal=fields.CharField(max_length=10)
    position_buy=fields.FloatField()
    position_sell=fields.FloatField()
    
    class Meta:
        table = 'candle'
        table_description = 'This table contains candle history'

    def __str__(self):
        return self.name

