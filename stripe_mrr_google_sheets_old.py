# General Setup

import sys
sys.path.append("/Users/dlite/projects/petaldata-python")
import petaldata
import petaldata.util

from dotenv import load_dotenv
load_dotenv(override=True)
import os

import pandas as pd
import datetime
from datetime import datetime

# Exporting to Google Sheets
import pygsheets

# Configuration

petaldata.api_base = 'http://localhost:3001'
petaldata.resource.stripe.api_key = os.getenv("STRIPE_API_KEY")
petaldata.storage.Local.dir = os.getenv("CACHE_DIR")
petaldata.storage.Local.enabled = True

petaldata.storage.S3.enabled = False
petaldata.storage.S3.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
petaldata.storage.S3.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
petaldata.storage.S3.bucket_name = 'petaldata-test2'

# Loads Stripe Invoices, using S3 for pickle file storage. 

invoices = petaldata.resource.stripe.Invoice()
invoices.load()

# Statuses can change, so fetch all invoices over the last 30 days
# TODO - only run this if loaded data from a pickle file
invoices.update(petaldata.util.days_ago(30))
# invoices.save()

# Authorize
# https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=scout-biz-metrics&authuser=1&organizationId=420515861971
gc=pygsheets.authorize(service_file='gdrive_service_account.json')

df_invoices = invoices.df

# Set to reporting timezone
TZ = 'America/Denver'

def set_tz(dataframe,tz):
    for col in dataframe.columns:
          if 'datetime64[ns' in str(dataframe[col].dtype):
            dataframe[col] = dataframe[col].dt.tz_convert(tz)
    return dataframe

df_invoices = set_tz(df_invoices,TZ)

def strip_tz(dataframe):
    dataframe = dataframe.copy()
    for col in dataframe.columns:
          if 'datetime64' in str(dataframe[col].dtype):
            dataframe[col] = dataframe[col].apply(lambda x:datetime.replace(x,tzinfo=None))
    return dataframe

# Setup dates

date = datetime.now()
# date = pd.Timestamp(date).floor(freq='D') - pd.offsets.MonthBegin(0) # looking at april
t=pd.Timestamp(date)
t=t.tz_localize(TZ)

cur_end=t#t.ceil(freq='D')

# Query filters
def annual_query(df):
    return df["subscription.plan.interval"] == 'year'

def time_range_query(df,start_time,end_time):
    return ((df.created >= start_time) & (df.created < end_time))  & (df.amount_due > 0)

def billing_status_query(df):
    return (df.status != 'draft') & (df.status != 'void')

# query filters
def by_day_query(df,start_time,end_time,manual=False):
    return time_range_query(df,start_time,end_time) & (df.billing_reason != "manual" if not manual else df.billing_reason == "manual") & billing_status_query(df)


# Handle annual subscriptions

def per_month(amount,interval):
    if interval == 'year':
        return amount / 12.0
    else:
        return amount

df_invoices['amount_due_per_month'] = df_invoices.apply(lambda row: per_month(row.amount_due,row["subscription.plan.interval"]), axis=1)
df_invoices['amount_paid_per_month'] = df_invoices.apply(lambda row: per_month(row.amount_paid,row["subscription.plan.interval"]), axis=1)




def add_simulated_annual_invoices(df):
    frames = []
    for index, row in df[annual_query(df) & (df.amount_due > 0)].iterrows():
        for datetime in pd.date_range(start=row["subscription.current_period_start"], 
                                  end=row["subscription.current_period_end"]-pd.offsets.MonthBegin(2), 
                                  freq='MS'):
            date = datetime.date()
            simulated_row = row.copy()
            simulated_row.name = row.name+"_"+str(date)
            simulated_row.date = datetime
            simulated_row.created = datetime
            simulated_row["simulated"] = 1
            frame = simulated_row.to_frame().transpose()
            frame.index.name = "id"
            frames.append(frame)

    return pd.concat([df]+frames,verify_integrity=True,sort=False)

df_invoices = add_simulated_annual_invoices(df_invoices)

# Generate monthly data

grouped = df_invoices[(df_invoices.billing_reason != "manual") & time_range_query(df_invoices,df_invoices.created.min(),cur_end) & billing_status_query(df_invoices)].groupby(pd.Grouper(key="created",freq="M")).agg(
    {"amount_due": "sum", "amount_paid": "sum",
    "amount_due_per_month": "sum", "amount_paid_per_month": "sum",
    "simulated": "sum",
    "paid": 'sum',
     "created": 'count',
    "customer_email": pd.Series.nunique}
)
grouped.rename(columns={"customer_email": 'customers', "simulated": 'ongoing_annual_subscriptions'},inplace=True)
grouped.sort_index(ascending=False).head()
# convert cents to dollars
grouped[['amount_due_per_month','amount_paid_per_month']]=grouped[['amount_due_per_month','amount_paid_per_month']]/100

# save monthly data to google sheets

print("Opening Google Sheet...")

# Must share sheet with "client_email" from JSON creds file
sh = gc.open('Copy of Revenue Reporting')

wks = sh.worksheet_by_title("Monthly MRR via Invoices")
print("\t...updating MRR worksheet")
wks.clear(fields="*")
wks.set_dataframe(strip_tz(grouped),(1,1), copy_index=True, nan="")
print("\t...Done.")

######## MTD

cur_start = cur_end.ceil(freq='D') - pd.offsets.MonthBegin()

# prev_end = cur_end - pd.DateOffset(months=1)
prev_end = cur_start
prev_start = prev_end.ceil(freq='D') - pd.offsets.MonthBegin()

print("MTD - comparing ({} - {}) to previous month ({} - {})".format(cur_start,cur_end,prev_start,prev_end))

# get invoices between prev_start and end, then sum 
prev_month = df_invoices[by_day_query(df_invoices,prev_start,prev_end)]

cur_month = df_invoices[by_day_query(df_invoices,cur_start,cur_end)]

# get invoices between prev_start and end, then sum 
prev_month = df_invoices[by_day_query(df_invoices,prev_start,prev_end)]
cur_month = df_invoices[by_day_query(df_invoices,cur_start,cur_end)]

def group_and_agg(df):
    grouped = df.groupby(pd.Grouper(key="created",freq="D")).agg(
        {'amount_paid_per_month': 'sum',
         'amount_due_per_month': 'sum', 
         'customer_email': pd.Series.nunique,
         'simulated': 'sum'}
    )
    grouped[['amount_paid_per_month']]=grouped[['amount_paid_per_month']]/100
    grouped[['amount_due_per_month']]=grouped[['amount_due_per_month']]/100
    return grouped.rename(columns={"customer_email": "customers", "simulated": "ongoing_annual_subscriptions"})
    
prev_month_by_day = group_and_agg(prev_month)
cur_month_by_day = group_and_agg(cur_month)

print(prev_month_by_day.shape)

df_mtd=cur_month_by_day.cumsum().reset_index().join(prev_month_by_day.cumsum().reset_index(), rsuffix=" (Previous Month)",
    how="outer")
df_mtd.index += 1 
df_mtd.index.name = 'Day'

wks = sh.worksheet_by_title("MTD")
print("\t...updating MTD worksheet")
wks.clear(fields="*")
wks.set_dataframe(df_mtd,(1,1), copy_index=True, nan="")
wks.cell('A1').value = df_mtd.index.name
print("\t...Done.")


current_invoices = df_invoices[time_range_query(df_invoices,cur_start,cur_end)]
print("\t...updating list of invoices for current month. invoices=",current_invoices.shape)
wks = sh.worksheet_by_title("Current Month Invoices")
wks.clear(fields="*")
wks.set_dataframe(strip_tz(current_invoices),(1,1), copy_index=True,nan="")
wks.cell('A1').value = df_invoices.index.name
print("\t...Done.")

### Monthly Invoices by Plan ID

print("Generating Monthly Invoices by Plan ID")

by_plan = df_invoices[(df_invoices.billing_reason != "manual") & time_range_query(df_invoices,df_invoices.created.min(),cur_end) & billing_status_query(df_invoices)].groupby([pd.Grouper(key="created",freq="M"),"subscription.plan.id"]).agg(
    {"amount_due_per_month": "sum", "amount_paid_per_month": "sum",
    "paid": 'sum',
     "created": 'count',
    "customer_email": pd.Series.nunique}
)
by_plan.rename(columns={"customer_email": 'customers'},inplace=True)
# convert cents to dollars
by_plan[['amount_due_per_month','amount_paid_per_month']]=by_plan[['amount_due_per_month','amount_paid_per_month']]/100

wks = sh.worksheet_by_title("Monthly Invoices by Plan ID")
print("\t...updating invoices by plan worksheet")
wks.clear(fields="*")
wks.set_dataframe(strip_tz(by_plan),(1,1), copy_index=True, nan="")
print("\t...Done.")

### Record updated time

wks = sh.worksheet_by_title("Summary")
wks.cell('I3').value = str(datetime.replace(cur_end,tzinfo=None))






