import pandas as pd
from delta_rest_client import DeltaRestClient
import os
# from mailer import send_email
import dotenv
import sys
dotenv.load_dotenv()
delta_client = DeltaRestClient(
  base_url='https://api.india.delta.exchange',
  api_key=os.getenv("DELTA_API_KEY"),
  api_secret=os.getenv("DELTA_API_SECRET")
)
switch_new=0
symbol_id={}
df_val = pd.read_csv("values.csv")
values_dict = dict(zip(df_val["symbol"], df_val["value"]))

path = "daily_products/BTC"

dfs = {}

for file in os.listdir(path):
    if file.endswith(".csv"):
        name = file.replace(".csv","")
        df = pd.read_csv(os.path.join(path, file))
        symbol_id.update(dict(zip(df["symbol"], df["id"])))
        # keep only needed columns
        df = df[["strike_price","symbol"]]
        
        # rename symbol column
        df = df.rename(columns={"symbol": name})
        
        dfs[name] = df

# merge horizontally
combined_df = dfs[list(dfs.keys())[0]]

for df in list(dfs.values())[1:]:
    combined_df = combined_df.merge(df, on="strike_price", how="outer")
combined_df = combined_df.dropna(subset=["put_options", "call_options", "move_options"])


tickers_df = pd.DataFrame(delta_client.get_ticker(''))[["symbol", "quotes"]]
ticker_lookup = tickers_df.set_index("symbol")["quotes"].to_dict()


# margin or funds
asset_id=pd.DataFrame(delta_client.get_assets())
asset_id=asset_id[asset_id['symbol']=='USD'][['id']].values[0][0]
wallet_dict=delta_client.get_balances(asset_id)


def get_bid_ask(symbol):
    quotes = ticker_lookup.get(symbol)
    # print(f"Symbol: {symbol}, Quotes: {quotes}")
    if quotes is None:
        return None, None

    return quotes.get("best_bid"), quotes.get("best_ask")


# def tender_check(strike_price, ask_put, ask_call, ask_move,bid_put, bid_call, bid_move):
#     ask_diff = ask_put + ask_call - bid_move
#     bid_diff = ask_move - (bid_put + bid_call)
#     ask_percent = (ask_diff / (ask_put + ask_call + ask_move)) * 100 
#     bid_percent = (bid_diff / (bid_put + bid_call + bid_move)) * 100 
#     # print(f"Strike: {strike_price}, Ask Percent: {ask_percent:.2f}%, Bid Percent: {bid_percent:.2f}%")
    
#     if(values_dict.get("twenty") == 0 and (ask_percent > 20 or bid_percent > 20)):
#         send_email(
#             "MOVE Arbitrage Opportunity",
#             f"Strike: {strike_price},Percent:20"
#         )
#         values_dict["twenty"] = 1
#         values_dict["fifteen"] = 1
#         values_dict["ten"] = 1
#     elif(values_dict.get("fifteen") == 0 and (ask_percent > 15 or bid_percent > 15)):
#         send_email(
#             "MOVE Arbitrage Opportunity",
#             f"Strike: {strike_price},Percent:15"
#         )
#         values_dict["fifteen"] = 1
#         values_dict["ten"] = 1
#     elif(values_dict.get("ten") == 0 and (ask_percent > 10 or bid_percent > 10)):
#         send_email(
#             "MOVE Arbitrage Opportunity",
#             f"Strike: {strike_price},Percent:10"
#         )
#         values_dict["ten"] = 1

def my_order_check(symbol, type):
    delta_client.place_order(
    product_id=symbol_id.get(symbol),
    size=1,
    side=type,
    order_type="market_order"
    )
def process_row(row):
    global switch_new
    bid_put, ask_put = get_bid_ask(row["put_options"])
    bid_call, ask_call = get_bid_ask(row["call_options"])
    bid_move, ask_move = get_bid_ask(row["move_options"])

    params = [bid_put, ask_put, bid_call, ask_call, bid_move, ask_move]

    # Only proceed if values exist and are not 0
    if all(p is not None and p != 0 for p in params):

        bid_put, ask_put, bid_call, ask_call, bid_move, ask_move = map(float, params)
        total_move_price = ask_move + bid_put + bid_call
        total_put_call_price = ask_put + ask_call + bid_move
        move_percent= (-ask_move+ (bid_put + bid_call)) / total_move_price * 100 if total_move_price != 0 else 0
        put_call_percent = (-(ask_put + ask_call) + bid_move) / total_put_call_price * 100 if total_put_call_price != 0 else 0
        
        current_balance=float(wallet_dict["available_balance"])
        if(move_percent>9 and current_balance>2):
            my_order_check(row["move_options"], "buy")
            my_order_check(row["put_options"], "sell")
            my_order_check(row["call_options"], "sell")
            switch_new=1
        elif(put_call_percent>9 and current_balance>2):
            my_order_check(row["move_options"], "sell")
            my_order_check(row["put_options"], "buy")
            my_order_check(row["call_options"], "buy")
            switch_new=1
        
        # tender_check(
        #     strike_price=row["strike_price"],
        #     ask_put=ask_put,
        #     ask_call=ask_call,
        #     ask_move=ask_move,
        #     bid_put=bid_put,
        #     bid_call=bid_call,
        #     bid_move=bid_move
        # )

for _, row in combined_df.iterrows():
    # print(_)
    # print(row)
    process_row(row)
    if switch_new == 1:
        break


df_val = pd.DataFrame(list(values_dict.items()), columns=["symbol", "value"])

df_val.to_csv("values.csv", index=False)

if switch_new == 1:
    print("found an opportunity, restarting")
    os.execv(sys.executable, [sys.executable] + sys.argv)
