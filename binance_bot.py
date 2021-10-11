from datetime import datetime
from logging import error, exception
import ccxt
import schedule
import time
import config
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


pd.set_option('display.max.rows', None)


exchange = ccxt.binance({
    'apiKey': config.BINANCE_API_KEY,
    'secret': config.BINANCE_SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # ←-------------- quotes and 'future'
    },    
})

from binance.client import Client

client = Client(config.BINANCE_API_KEY, config.BINANCE_SECRET_KEY)


FRST_COIN = 'DOGE'
SCND_COIN = 'USDT'
PAIR = f'{FRST_COIN}/{SCND_COIN}'
PAIR_BNC = f'{FRST_COIN}{SCND_COIN}'
AMOUNT = 20000 # Количество в DOGE с учетом плеча. Т.е. если у нас 100$, плечо 10, курс 0.25, то 100 * 10 / 0.25 = 4000


TIMEFRAME = '3m'
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
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period=period)
    df['upperband'] = hl2 + atr_multiplier * df['atr']
    df['lowerband'] = hl2 - atr_multiplier * df['atr']
    df['in_uptrend'] = True

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
current_order = {}

def close_current_order():
    '''Закрывает любую текущую позицию'''

    res = client.futures_position_information(
        symbol='DOGEUSDT',
    )
    print(f'Текущая позиция: {res}')
    amt = float(res[0]['positionAmt']) # стоимость позиции в DOGE с учетом плеча

    # создаем противоположный ордер с той же суммой
    act = 'SELL' if amt > 0 else 'BUY'
    amount = abs(amt)
    clear_order = None
    if amount > 1e-6:
        clear_order = client.futures_create_order(
            symbol=PAIR_BNC,
            side=act,
            type="MARKET",
            quantity=amount)
        print(f'Отменяем ордер: {clear_order}')
    
    return clear_order


def check_buy_sell_signals(df):
    '''Выдает сигналы покупать или продавать'''
    global is_in_long_position
    global current_order
    print(df.tail(5))
    last_row_index = len(df.index) - 1
    prev_row_index = last_row_index - 1
 
    if not df['in_uptrend'][prev_row_index] and df['in_uptrend'][last_row_index]:
        print("buy")
        # if not in_position:
        #     order = exchange.create_market_buy_order(PAIR, AMOUNT)
        #     print(order)
        #     in_position = True
        # else:
        #     print('already in position, nothing to do')

        if not is_in_long_position:
            close_current_order()
            current_order = client.futures_create_order(
                symbol=PAIR_BNC,
                side="BUY",
                type="MARKET",
                quantity=AMOUNT)

            is_in_long_position = True
            print(current_order)
        else:
            print('already in long position, nothing to do')

       

    if df['in_uptrend'][prev_row_index] and not df['in_uptrend'][last_row_index]:
        print("sell")
        # if in_position:
        #     order = exchange.create_market_sell_order(PAIR, AMOUNT)
        #     print(order)
        #     in_position = False
        # else:
        #     print('You are not in position, nothing to sell')

        if is_in_long_position:
            close_current_order()
            current_order = client.futures_create_order(
                symbol=PAIR_BNC,
                side="SELL",
                type="MARKET",
                quantity=AMOUNT)

            is_in_long_position = False
            print(current_order)
        else:
            print('already in short position, nothing to do')


def run_bot():
    try:
        print(f'fetching new bars for {datetime.now().isoformat()}')
        bars = exchange.fetch_ohlcv(PAIR, timeframe=TIMEFRAME, limit=TREND_LIMIT)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        supertrend_data = supertrend(df, period=PERIOD)

        check_buy_sell_signals(supertrend_data)
    except Exception as e:
        print(e)

def init_bot():
    global current_order
    # try: Надо обернуть обработчиками ошибок, чтобы не висеть в позиции. В крайнем случае пытаться закрыться
    print(f'fetching new bars for {datetime.now().isoformat()}')
    bars = exchange.fetch_ohlcv(PAIR, timeframe=TIMEFRAME, limit=TREND_LIMIT)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    supertrend_data = supertrend(df, period=PERIOD)

    print(df.tail(5))
    last_row_index = len(df.index) - 1
    close_current_order()

    if df['in_uptrend'][last_row_index]:
        print("buy")

        current_order = client.futures_create_order(
            symbol=PAIR_BNC,
            side="BUY",
            type="MARKET",
            quantity=AMOUNT)

        print(current_order)
    

    if not df['in_uptrend'][last_row_index]:
        print("sell")

        current_order = client.futures_create_order(
            symbol=PAIR_BNC,
            side="SELL",
            type="MARKET",
            quantity=AMOUNT)
        
        print(current_order)

    # except Exception as e:
    #     print(e)    

init_bot()

schedule.every(30).seconds.do(run_bot)


while True:
    schedule.run_pending()
    time.sleep(1)




#### Всяко-разно-полезно... ####

# balances = exchange.fetch_balance()['info']['balances']
# for balance in balances:
#     if float(balance['free']) > 1e-8 or float(balance['locked']) > 1e-8:
#         print(balance) 

# markets = exchange.load_markets()
# # for market in markets:
# #     print(market)


# ticker = exchange.fetch_ticker('BTC/USDT')
# print(ticker)

# ohlc = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=5)

# for candle in ohlc:
#     print(candle)

# order_book = exchange.fetch_order_book('BTC/USDT')
# for order in order_book:
#     print(order_book)


# from variable id
# exchange_id = 'binance'
# exchange_class = getattr(ccxt, exchange_id)
# exchange = exchange_class({
#     'apiKey': 'YOUR_API_KEY',
#     'secret': 'YOUR_SECRET',
#     'timeout': 30000,
#     'enableRateLimit': True,
# })