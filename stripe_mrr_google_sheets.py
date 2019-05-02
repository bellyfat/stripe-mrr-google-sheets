# General Setup

from dotenv import load_dotenv
load_dotenv(override=True)

import sys
import petaldata
import petaldata.util
import os
import json
import pandas as pd
import datetime
from datetime import datetime

# Exporting to Google Sheets
import google
from google.oauth2 import service_account
import pygsheets

# Configuration

petaldata.api_base = 'https://petaldata.herokuapp.com'
petaldata.resource.stripe.api_key = os.getenv("STRIPE_API_KEY")
petaldata.storage.Local.dir = os.getcwd() + "/tmp/"

petaldata.storage.Local.enabled = False
petaldata.storage.S3.enabled = True

petaldata.storage.S3.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
petaldata.storage.S3.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
petaldata.storage.S3.bucket_name = os.getenv("AWS_BUCKET")

# Loads Stripe Invoices, using S3 for pickle file storage. 

invoices = petaldata.resource.stripe.Invoice()
invoices.load()

# Statuses can change, so fetch all invoices over the last 30 days
# TODO - only run this if loaded data from a pickle file
invoices.update(petaldata.util.days_ago(45))
invoices.save()

# Authorize Google Sheets
# https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=scout-biz-metrics&authuser=1&organizationId=420515861971
creds = service_account.Credentials.from_service_account_info(json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")))
gc = pygsheets.authorize(custom_credentials=creds.with_scopes(['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.metadata.readonly']))

# Generate the report dataframe

report = petaldata.resource.stripe.reports.MRRByMonth(invoices)
df = report.to_frame(tz='America/Denver')

# Save report to Google Sheets

print("Opening Google Sheet...")

# Must share sheet with "client_email" from JSON creds file
sh = gc.open('Copy of Revenue Reporting')

wks = sh.worksheet_by_title("Monthly MRR via Invoices")
print("\t...updating MRR worksheet")
wks.clear(fields="*")
wks.set_dataframe(df,(1,1), copy_index=True, nan="")
print("\t...Done.")

### Record updated time

wks = sh.worksheet_by_title("Summary")
wks.cell('I3').value = str(datetime.now())
