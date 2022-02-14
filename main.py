import config
from binance.client import Client

from datetime import datetime
import pandas as pd
import time

####################################################################################################################################
from models import Candle, Candle_Pydantic, CandleIn_Pydantic
from tortoise import Tortoise, run_async


async def init():
    await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})
    await Tortoise.generate_schemas(safe=True)

if __name__ == '__main__':
    run_async(init()) # run_async по выполнению всех операций init() завершает автоматически соединение с БД

# Для нового обращения к базе данных надо заново создавать новое подключение
# На данный момент получилось только так:
# await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})

async def add_to_DB(timestamp, balance, signal, position_buy, position_sell):
    await Tortoise.init(db_url='sqlite://sql_app.db', modules={'models': ['__main__']})
    await Candle.create(timestamp=timestamp, balance=balance, signal=signal, position_buy=position_buy, position_sell=position_sell)

####################################################################################################################################

pd.set_option('display.max.rows', None)

#Initialise the client
client = Client(config.BINANCE_API_KEY, config.BINANCE_SECRET_KEY)

balance=10000.0
total_balance=balance #Данное значение обновляется во время закрытия сделки и заносится в БД
position_buy=0.0
position_sell=0.0
comission=0.0005 # 1=100%, 0.001=0.1%

FRST_COIN = 'DOGE'
SCND_COIN = 'USDT'
PAIR = f'{FRST_COIN}/{SCND_COIN}'
PAIR_BNC = f'{FRST_COIN}{SCND_COIN}'
AMOUNT = 20000 # Количество в DOGE с учетом плеча. Т.е. если у нас 100$, плечо 10, курс 0.25, то 100 * 10 / 0.25 = 4000

#TIMEFRAME = '3m'
TREND_LIMIT = 100
PERIOD = 3


def tr(df):
    
    df['previous_close'] = df['close'].shift(1)
    df['high-low'] = df['high'] - df['low']
    df['high-pc'] = abs(df['high'] - df['previous_close'])
    df['low-pc'] = abs(df['low'] - df['previous_close'])
    tr = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    return tr


def atr(df, period=14):
    df['tr'] = tr(df)
    the_atr = df['tr'].rolling(period).mean()
    return the_atr


def supertrend(df, period=14, atr_multiplier=3):
    global prev_in_uptrend

    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period=period)
    df['upperband'] = hl2 + atr_multiplier * df['atr']
    df['lowerband'] = hl2 - atr_multiplier * df['atr']
    #df['in_uptrend'] = True
    # Необходимо запоминать как минимум последнее значение каждого запроса истории
    # Иначе каждый новый запрос начинается по умолчанию с True
    df['in_uptrend'] = prev_in_uptrend

    for current in range(1, len(df.index)):
        previous = current -1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
    return df


is_in_long_position = False
#current_order = {}


def close_current_order(df):
    # '''Закрывает любую текущую позицию'''

    # res = client.futures_position_information(
    #     symbol='DOGEUSDT',
    # )
    # print(f'Текущая позиция: {res}')
    # amt = float(res[0]['positionAmt']) # стоимость позиции в DOGE с учетом плеча

    # # создаем противоположный ордер с той же суммой
    # act = 'SELL' if amt > 0 else 'BUY'
    # amount = abs(amt)
    # clear_order = None
    # if amount > 1e-6:
    #     clear_order = client.futures_create_order(
    #         symbol=PAIR_BNC,
    #         side=act,
    #         type="MARKET",
    #         quantity=amount)
    #     print(f'Отменяем ордер: {clear_order}')
    
    # return clear_order
    global is_in_long_position
    global position_buy, position_sell, balance, total_balance

    last_row_index = len(df.index) - 1
    prev_row_index = last_row_index - 1

    if (is_in_long_position):
        print("Мы в длинной позиции, поэтому закрываем длинные позиции")
        position_buy=AMOUNT*df['close'][last_row_index]
        print(f'Продаем лонг: {position_buy}')
        balance = balance + (1-comission)*position_buy
        position_buy=0
        print('-----------------------------------------------------------------------------------------------')
        print(f'balance: {balance}')
    else:
        print("Мы в короткой позиции, поэтому закрываем короткие позиции")
        position_sell=AMOUNT*df['close'][last_row_index]
        print(f'Откупаем шорт: {position_sell}')
        balance = balance - (1+comission)*position_sell
        position_sell=0
        print('-----------------------------------------------------------------------------------------------')
        print(f'balance: {balance}')
    print('-----------------------------------------------------------------------------------------------')
    
    total_balance=balance


def check_buy_sell_signals(df):
    '''Выдает сигналы покупать или продавать'''
    global is_in_long_position
    #global current_order
    global position_buy, position_sell, balance
    #print(df.tail(5))
    last_row_index = len(df.index) - 1
    prev_row_index = last_row_index - 1
 
    if not df['in_uptrend'][prev_row_index] and df['in_uptrend'][last_row_index]:
        # print("buy")
        # # if not in_position:
        # #     order = exchange.create_market_buy_order(PAIR, AMOUNT)
        # #     print(order)
        # #     in_position = True
        # # else:
        # #     print('already in position, nothing to do')

        # if not is_in_long_position:
        #     close_current_order()
        #     current_order = client.futures_create_order(
        #         symbol=PAIR_BNC,
        #         side="BUY",
        #         type="MARKET",
        #         quantity=AMOUNT)

        #     is_in_long_position = True
        #     print(current_order)
        # else:
        #     print('already in long position, nothing to do')
        
        print('{0} long/short_signal: {1}'.format(df['timestamp'][last_row_index],df['in_uptrend'][last_row_index]))
        print("Функция check_buy_sell_signals() - Сигнал на ПОКУПКУ")

        if not is_in_long_position:
            close_current_order(df)
            print("Выставляем заявку в ЛОНГ")
            position_buy=AMOUNT*df['open'][last_row_index]
            print(f'position_buy: {position_buy}')
            print()
            balance=balance-(1+comission)*position_buy
            is_in_long_position = True
        else:
            print('already in long position, nothing to do')
            print()
       
    if df['in_uptrend'][prev_row_index] and not df['in_uptrend'][last_row_index]:
        # print("sell")
        # # if in_position:
        # #     order = exchange.create_market_sell_order(PAIR, AMOUNT)
        # #     print(order)
        # #     in_position = False
        # # else:
        # #     print('You are not in position, nothing to sell')

        # if is_in_long_position:
        #     close_current_order()
        #     current_order = client.futures_create_order(
        #         symbol=PAIR_BNC,
        #         side="SELL",
        #         type="MARKET",
        #         quantity=AMOUNT)

        #     is_in_long_position = False
        #     print(current_order)
        # else:
        #     print('already in short position, nothing to do')
 
        #print('{0} long/short_signal: {1}'.format(df['timestamp'][last_row_index],df['in_uptrend'][last_row_index]))
        print("Функция check_buy_sell_signals() - Сигнал на ПРОДАЖУ")

        if is_in_long_position:
            close_current_order(df)
            print("ВЫСТАВЛЯЕМ ЗАЯВКУ В ШОРТ")
            position_sell=AMOUNT*df['open'][last_row_index]
            print(f'position_sell: {position_sell}')
            print()
            balance = balance + (1-comission)*position_sell
            is_in_long_position = False
        else:
            print('already in short position, nothing to do')
            print()


# функция запрашивает частями историю свечек и далее объединяет нужные данные в один список
# возвращает истрию свечек, где limit=количество запрашиваемых свечек, N-количество запросов
def get_candles_list(limit=50, N=2):
    candles_full_list=[]
    current_time_5MINUTE=client.get_klines(symbol='DOGEBUSD', interval=Client.KLINE_INTERVAL_5MINUTE, limit=1)
    lenght_5MINUTE=300000
    for i in range(1,N+1):
        temp=client.get_klines( 
            symbol='DOGEBUSD', 
            interval=Client.KLINE_INTERVAL_5MINUTE,
            endTime=current_time_5MINUTE[0][0]-limit*lenght_5MINUTE*(N-i), 
            limit=limit
            )
        for i in range(len(temp)):
            candles_full_list.append(temp[i])
    # Выбираю только 6 нужных мне столбцов с которыми буду работать
    candles=[]
    for i in range(len(candles_full_list)):
        candles.append(list(map(float, candles_full_list[i][0:6])))
    return candles


def init_bot(bars):
    #global current_order
    global position_buy, position_sell, balance, is_in_long_position
    global prev_in_uptrend
    # try: Надо обернуть обработчиками ошибок, чтобы не висеть в позиции. В крайнем случае пытаться закрыться
    #print(f'Fetching new bars for {datetime.now().isoformat()}')
    #bars = exchange.fetch_ohlcv(PAIR, timeframe=TIMEFRAME, limit=TREND_LIMIT)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    #df = pd.DataFrame(bars[:-1] , columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    supertrend_data = supertrend(df, period=PERIOD)
    # print(df)
    # print()
    last_row_index = len(df.index) - 1
    #close_current_order()

    if df['in_uptrend'][last_row_index]:
        # print("buy")

        # current_order = client.futures_create_order(
        #     symbol=PAIR_BNC,
        #     side="BUY",
        #     type="MARKET",
        #     quantity=AMOUNT)

        # print(current_order)
        
        position_buy=AMOUNT*df['high'][last_row_index]
        balance=balance-(1+comission)*position_buy
        is_in_long_position = True
        print('{0} long/short_signal: {1}'.format(df['timestamp'][last_row_index],df['in_uptrend'][last_row_index]))
        print(f'position_buy: {position_buy}, position_sell: {position_sell}')

    if not df['in_uptrend'][last_row_index]:
        # print("sell")

        # current_order = client.futures_create_order(
        #     symbol=PAIR_BNC,
        #     side="SELL",
        #     type="MARKET",
        #     quantity=AMOUNT)
        
        # print(current_order)

        position_sell=AMOUNT*df['low'][last_row_index]
        balance = balance + (1-comission)*position_sell
        is_in_long_position = False
        print('{0} long/short_signal: {1}'.format(df['timestamp'][last_row_index],df['in_uptrend'][last_row_index]))
        print(f'position_buy: {position_buy}, position_sell: {position_sell}')

        prev_in_uptrend=df['in_uptrend'][last_row_index]

    # except Exception as e:
    #     print(e)   


def run_bot(bars):
    global position_buy, position_sell
    global prev_in_uptrend

    try:
        #print(f'fetching new bars for {datetime.now().isoformat()}')
        #bars = exchange.fetch_ohlcv(PAIR, timeframe=TIMEFRAME, limit=TREND_LIMIT)
        df = pd.DataFrame(bars , columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        #df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        supertrend_data = supertrend(df, period=PERIOD)
        # print(df)
        # print()
        
        last_row_index = len(df.index) - 1

        print('{0} long/short_signal: {1}'.format(df['timestamp'][last_row_index],df['in_uptrend'][last_row_index]))
        print(f'position_buy: {position_buy}, position_sell: {position_sell}')
        run_async(add_to_DB(
                        str(df['timestamp'][last_row_index]), 
                        total_balance, str(df['in_uptrend'][last_row_index]), 
                        float(position_buy), 
                        float(position_sell))
                        )
        
        check_buy_sell_signals(supertrend_data)

        prev_in_uptrend=df['in_uptrend'][last_row_index]

    except Exception as e:
        print(e)

####################################################################################################################################

prev_in_uptrend=True # Здесь хранится значение тренда предыдущего запуска supertrend()
candles=[] # Полный список свечек из Binance
candles=get_candles_list() # запрашиваем свечки для выполнения функции init_bot()
# Выбираем из полного списка candles, (PERIOD+1) строчек
# Например, если PERIOD=3, выбираем 3 свечки "истории" и четвертая свечка - текущая
bars=[]
bars=candles[:][0:PERIOD+1]

init_bot(bars)

# Запускаем проход по свечкам
for i in range(1,len(candles)-PERIOD):  
    bars=candles[:][i:i+PERIOD+1]
    run_bot(bars)

####################################################################################################################################

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise
from typing import List

app = FastAPI(title="Tortoise ORM FastAPI example")


class Status(BaseModel):
    message: str


@app.get("/candles", response_model=List[Candle_Pydantic])
async def get_candles():
    return await Candle_Pydantic.from_queryset(Candle.all())


register_tortoise(
    app,
    db_url='sqlite://sql_app.db',
    modules={"models": ["models"]},
    #generate_schemas=True,
    add_exception_handlers=True,
)


if __name__ == '__main__':
    uvicorn.run('main:app', port=8000, host='127.0.0.1', reload=True)

####################################################################################################################################