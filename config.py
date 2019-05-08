import os
import petaldata

petaldata.api_base = 'https://petaldata.herokuapp.com'
petaldata.resource.stripe.api_key = os.getenv("STRIPE_API_KEY")
petaldata.storage.Local.dir = os.getcwd() + "/tmp/"

petaldata.storage.Local.enabled = False
petaldata.storage.S3.enabled = True

petaldata.storage.S3.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
petaldata.storage.S3.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
petaldata.storage.S3.bucket_name = os.getenv("AWS_BUCKET")

# Make consistent with your TZ in Stripe's account settings: https://dashboard.stripe.com/account
TZ = 'America/Denver'
