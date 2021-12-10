# Twitter Scraper module
import tweepy

# dates module
from itertools import count
import time
from datetime import datetime, timedelta

# trading terminal
import pyotp
import robin_stocks.robinhood as r

# Store Twitter credentials from dev account
consumer_key = "***"
consumer_secret = "***"
access_key = "***"
access_secret = "***"

# text sentiment API key
sentiment_key = "***"

# Pass twitter credentials to tweepy via its OAuthHandler
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth)

# connect to the trade account without specifying a password and a server
# totp = pyotp.TOTP("My2factorAppHere").now()
# login = r.login("***", "***", mfa_code=totp)
login = r.login("***", "***")


# Get Zack Morris's latest tweet
# Return: last_id, ticker
def get_zacks_tweet_ticker(param_last_id):

    """Get Zack's last tweet by user ID"""
    tweets = tweepy.Cursor(api.user_timeline,
                           user_id="373620043",
                           tweet_mode='extended').items(1)
    tweets_info = [(tweet.id,
                    tweet.entities['symbols'],
                    tweet.full_text)
                   for tweet in tweets][0]

    if tweets_info[0] == param_last_id:
        return param_last_id, None

    print()
    print(datetime.now())
    print("Zack tweets: ")
    print(tweets_info[2])

    if len(tweets_info[1]) == 0:
        print("No ticker detected. ")
        return tweets_info[0], None

    print("Ticker $%s detected." % tweets_info[1][0]['text'])

    return tweets_info[0], tweets_info[1][0]['text']


def trade(param_last_id, param_amount):
    """ Check if 5% gains or 5% loss is achieved"""
    if datetime.now().replace(hour=7, minute=30, second=0, microsecond=0) <= datetime.now() \
            <= datetime.now().replace(hour=14, minute=0, second=0, microsecond=0):
        my_stocks = r.build_holdings()
        for key, value in my_stocks.items():
            if float(value['percent_change']) >= 20.0 or float(value['percent_change']) <= -20.0:
                print()
                print(datetime.now())
                if float(value['percent_change']) >= 20.0:
                    print('$' + key + ' achieves %.2f' % float(value['percent_change']) + '% gain.', end=' ')
                else:
                    print('$' + key + ' achieves %.2f' % -float(value['percent_change']) + '% loss.', end=' ')
                orders = r.orders.find_stock_orders(symbol=key)

                if len(orders) > 0 and orders[0]['side'] == 'sell' and orders[0]['state'] == 'queued':
                    print("The sell order has been placed.")
                else:
                    if float(value['percent_change']) >= 30.0 or float(value['percent_change']) <= -30.0:
                        day_trades = r.account.get_day_trades()
                        num_day_trades = len(day_trades['equity_day_trades'])
                        if num_day_trades == 3:
                            print("Have done 3 day trades in the past 5 business days. Not selling this ticker.")
                        else:
                            print("Placing the sell order ... ")
                            r.orders.order_sell_fractional_by_quantity(key, value['quantity'])
                    else:
                        buy_date = [order['last_transaction_at']
                                    for order in orders if order['side'] == 'buy' and order['state'] == 'filled'][0][:10]
                        if (datetime.today() - datetime.strptime(buy_date, '%Y-%m-%d')).days == 0:
                            print("Buy and sell at the same day. Not doing day trades for this amount of gain/loss. ")
                        else:
                            print("Placing the sell order ... ")
                            r.orders.order_sell_fractional_by_quantity(key, value['quantity'])

    """Check if Zack Morris mentioned some ticker"""
    new_last_id, ticker = get_zacks_tweet_ticker(param_last_id)

    if ticker is None:
        return new_last_id

    # Only place orders at market hours
    if datetime.now().replace(hour=7, minute=30, second=0, microsecond=0) > datetime.now() or \
            datetime.now() > datetime.now().replace(hour=14, minute=0, second=0, microsecond=0):
        return new_last_id

    orders = r.orders.find_stock_orders(symbol=ticker)
    orders = [order for order in orders if order['state'] != 'cancelled']

    # First check if we already placed an order
    if len(orders) > 0 and orders[0]['side'] == 'buy' and orders[0]['state'] == 'queued':
        print("The buy order for %s has been placed." % ticker)
        return new_last_id

    # Then check if we already hold it
    if ticker in r.build_holdings().keys():
        print("Already hold %s." % ticker)
        return new_last_id

    # Then check if we sold it within 3 business days
    if len(orders) > 0 and orders[0]['side'] == 'sell' and orders[0]['state'] == 'filled':
        last_transaction_day = datetime.strptime(orders[0]['last_transaction_at'][:10], '%Y-%m-%d')
        dates = (last_transaction_day + timedelta(idx + 1)
                 for idx in range((datetime.today() - last_transaction_day).days))
        num_business_days = sum(1 for day in dates if day.weekday() < 5)

        if num_business_days <= 1:
            print("I sold %s on %s, within 2 business days prior to today." % (ticker, orders[0]['last_transaction_at'][:10]))
            return new_last_id

    portfolio_cash = float(r.profiles.load_account_profile()['portfolio_cash'])
    print("Current portfolio cash amount: $%.2f" % portfolio_cash)
    if portfolio_cash > param_amount:
        print("Buy %s worth $%.2f" % (ticker, param_amount))
        r.orders.order_buy_fractional_by_price(ticker, param_amount)
    else:
        print("No enough cash. ")

    return new_last_id


# execute code every minute
if __name__ == '__main__':
    print('Press Ctrl-C / Ctrl-Q to stop.')
    last_id = 1468789830196903939
    amount = 5.00
    for i in count():
        last_id = trade(last_id, amount)
        time.sleep(10)
