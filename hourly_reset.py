import pandas as pd
from datetime import datetime, timedelta,time
from zoneinfo import ZoneInfo
from delta_rest_client import DeltaRestClient
import os
from dotenv import load_dotenv
from mailer import send_email
load_dotenv()
delta_client = DeltaRestClient(

  base_url='https://api.india.delta.exchange',
  api_key=os.getenv("DELTA_API_KEY"),
  api_secret=os.getenv("DELTA_API_SECRET")
)
now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
expiryTime=time(17,30)
if now_ist.time() > expiryTime:
    expiryDate=datetime.now() + timedelta(days=1)
else:    
    expiryDate=datetime.now()
products = delta_client.get_product('')
products=pd.DataFrame(products)
products=products.loc[products['trading_status']=='operational']
products['settlement_time']=pd.to_datetime(products['settlement_time'],utc=True)
products['expiry']=products['settlement_time'].dt.date
cols = ["symbol","strike_price","contract_type","contract_unit_currency","id"]

products = products.loc[
    (products.contract_type.isin(["put_options","call_options","move_options"])) &
    (products.expiry == expiryDate.date()),
    cols
]
products = products.sort_values("strike_price")


# saving to directory
base_dir = "daily_products"

for (ct, cur), df in products.groupby(["contract_type","contract_unit_currency"]):

    path = f"{base_dir}/{cur}"
    os.makedirs(path, exist_ok=True)

    df.to_csv(f"{path}/{ct}.csv", index=False)




df = pd.read_csv("values.csv")

df["value"] = 0

df.to_csv("values.csv", index=False)



#asset increase mail
asset_id=pd.DataFrame(delta_client.get_assets())
asset_id=asset_id[asset_id['symbol']=='USD'][['id']].values[0][0]
wallet_dict=delta_client.get_balances(asset_id)
balance=float(wallet_dict["balance"])
with open("funds.txt", "r") as f:
    current_value = float(f.read().strip())
balance_percent=(balance-current_value)/current_value*100 if current_value != 0 else 0
# print("percent change in balance:", balance_percent)
if balance_percent>10:
    send_email("Balance Alert", f"Your balance has increased by {balance_percent:.2f}%. Previous balance: {current_value:.2f}, Current balance: {balance:.2f}")
    with open("funds.txt", "w") as f:
        f.write(str(balance))
if balance_percent<-10:
    send_email("Balance Alert", f"Your balance has decreased by {balance_percent:.2f}%. Previous balance: {current_value:.2f}, Current balance: {balance:.2f}")
    with open("funds.txt", "w") as f:
        f.write(str(balance))
