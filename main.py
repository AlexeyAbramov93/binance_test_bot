from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


class Coin(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, description='Name of the cryptocurrency')
    price=fields.FloatField()
    datetime = fields.DatetimeField(auto_now_add=True, description='Created datetime')
    
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


async def run():
    await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})
    await Tortoise.generate_schemas()

    bitcoin=Coin_type(name='Bitcoin')
    altcoin=Coin_type(name='Altcoin')
    token=Coin_type(name='Token')
    stablecoin=Coin_type(name='Stablecoin')

    await bitcoin.save()
    await altcoin.save()
    await token.save()
    await stablecoin.save()

    await Coin(name='Test name #1', price=0.01, coin_type=bitcoin).save()
    await Coin(name='Test name #2', price=0.02, coin_type=altcoin).save()
    await Coin(name='Test name #3', price=0.03, coin_type=token).save()
    await Coin(name='Test name #4', price=0.04, coin_type=stablecoin).save()
    await Coin(name='Test name #5', price=0.05, coin_type=stablecoin).save()
    await Coin(name='Test name #6', price=0.06).save()

if __name__ == '__main__':
    run_async(run())