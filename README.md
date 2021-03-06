# Stripe Revenue Analysis to Google Sheets

This script runs a series of PetalData Stripe revenue reports, updating a specified Google Sheet with the output.

## Configuration

The following environment variables are required:

```
# Read only access to invoices
STRIPE_API_KEY=""

# Requires S3 read/write access
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_BUCKET=""

# The contents of the service account creds file provided by Google in JSON format
GOOGLE_SERVICE_ACCOUNT_INFO = {}

# Name of the Google Sheet the script will update.
# The user associated wit the Google auth creds must have read/write access to this sheet.
GOOGLE_SHEET=""
```

Optional:

```
SENTRY_DSN=""
SENTRY_ENVIRONMENT=""
```

## Development

```
pipenv install --dev
```

To examine output after running the script:

```
python -i stripe_mrr_google_sheets.py
```

Setting the env. var `DEV=true` will:

* Prevent fetching invoice updates (takes time)
* Load the `petaldata` package from disk. I haven't had much luck w/`Pipfile` `[dev-packages]`.

## Deployment

The app can be deployed to Heroku. Follow these steps:

* Create a Heroku app. Use GitHub for the deployment method and wire up this repo.
* Provide values for the [environment variables](#Configuration) as Heroku config vars.
* Install the Heroku Scheduler addon via `heroku addons:create scheduler:standard`.
* Open scheduler via `heroku addons:open scheduler`.
* Add a job to run every hour. Enter `python stripe_mrr_google_sheets.py` for the job.

### Debugging

You can run the script via the Heroku CLI:


```
heroku run "python stripe_mrr_google_sheets.py"
```

You can also enter interactive mode after running the script via the `-i` flag:

```
heroku run "python -i stripe_mrr_google_sheets.py"
```

`CTRL+C` to exit.
