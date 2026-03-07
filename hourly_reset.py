import pandas as pd
from datetime import datetime, timedelta,time
from zoneinfo import ZoneInfo
from delta_rest_client import DeltaRestClient
import os
from dotenv import load_dotenv
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
products['settlement_time']=pd.to_datetime(products['settlement_time'],utc=True)
products['expiry']=products['settlement_time'].dt.date
cols = ["symbol","strike_price","contract_type","contract_unit_currency"]

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
