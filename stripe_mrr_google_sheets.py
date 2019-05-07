import os

from dotenv import load_dotenv
load_dotenv(override=True)

# Load+Configure Sentry as early as possible to catch exceptions.
# Sentry is configured here vs. config so we can report import errors.
import sentry_sdk
from sentry_sdk import capture_exception
sentry_sdk.init(os.getenv("SENTRY_DSN"))

import sys
import petaldata
import petaldata.util
from petaldata.resource.stripe.reports import *
import json
import pandas as pd
import datetime
from datetime import datetime

# Exporting to Google Sheets
import google
from google.oauth2 import service_account
import pygsheets

import config

# Load Stripe Invoices
invoices = petaldata.resource.stripe.Invoice()
invoices.load()

# Statuses can change, so fetch all invoices over the last 45 days. Invoices beyond this
# timeframe will not be updated.
# TODO - only run this if loaded data from a pickle file
invoices.update(petaldata.util.days_ago(45))
invoices.save()

# Authorize Google Sheets
creds = service_account.Credentials.from_service_account_info(json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")))

# To re-run month end:
# end_time = pd.Timestamp(datetime.now()).floor(freq='D') - pd.offsets.MonthBegin(1)
end_time = datetime.now()
reports = petaldata.resource.stripe.reports.all(AdjustedInvoices(invoices,config.TZ, end_time=end_time),config.TZ, end_time=end_time)
list(map(lambda report: report.to_gsheet(creds,os.getenv("GOOGLE_SHEET")),reports))

# To debug a single report:
# report = Summary(invoices,tz=config.TZ,end_time=end_time)
# # frame = report.to_frame()
# report.to_gsheet(creds,os.getenv("GOOGLE_SHEET"))

sys.stdout.flush()