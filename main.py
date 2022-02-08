from models import Coin_type, Coin
from tortoise import Tortoise, run_async

import random


async def init():
    await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})
    await Tortoise.generate_schemas(safe=True)

    bitcoin=await Coin_type.create(name='Bitcoin')
    altcoin=await Coin_type.create(name='Altcoin')
    token=await Coin_type.create(name='Token')
    stablecoin=await Coin_type.create(name='Stablecoin')
    
    for i in range(1,15):
        name='Test {}'.format(i)
        await Coin.create(name=name, price=random.random(), coin_type=await Coin_type.get(id=random.randint(1,4)))

if __name__ == '__main__':
    run_async(init()) # run_async по выполнению всех операций init() завершает автоматически соединение с БД

# Для нового обращения к базе данных надо заново создавать новое подключение
# На данный момент получилось только так:
# await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})

async def edit():
    await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})


    await Coin_type.create(name='Stablecoin_NEW')
    await Coin_type.filter(id=1).update(name="Bitcoin_NEW")


run_async(edit())
