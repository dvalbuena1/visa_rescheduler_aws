# visa_rescheduler - AWS

US VISA (ais.usvisa-info.com) appointment re-scheduler - Colombian adaptation

With the extension to be deployed in AWS as a Lambda function

## Prerequisites

- Having a US VISA appointment scheduled already
- API token from Pushover and/or a Sendgrid (for notifications)

### Local

- Google Chrome installed (to be controlled by the script)
- Python v3 installed (for running the script)

### AWS

- Docker installed (to create the image)
- AWS credentials configured
- Serverless framework installed (to deploy the image)

## Initial Setup

- Create a `config.ini` file with all the details required
- Install the required python packages: `pip install -r requirements.txt`

## Executing the script

### Local
- Simply run `python -c "import setup; setup.as_loop()`

### AWS
- Simply run `python -c "import setup; setup.as_lambda_function()"`


That's it!

## Acknowledgement

Thanks to @uxDaniel and all those who have contributed to this project.

[Original repo](https://github.com/uxDaniel/visa_rescheduler)
