# visa_rescheduler - AWS

US VISA (ais.usvisa-info.com) appointment re-scheduler - Colombian adaptation

With the extension to be deployed in AWS as a Lambda function

## Prerequisites

- Having a US VISA appointment scheduled already
- API token from Pushover and/or a Sendgrid for notifications (optional)
- Python v3 installed (for running the script)

### Local

- Google Chrome installed (to be controlled by the script)

### AWS

- Docker installed (to create the image)
- [AWS credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html) configured
- [Serverless framework](https://www.serverless.com/framework/docs/getting-started#installation) installed (to deploy the image)

## Initial Setup

- Create a `config.ini` file with all the details required in the `config.ini.example`

## Executing the script

### Local
- Install the required python packages: `pip install -r requirements.txt`
- Simply run `python -c "import setup; setup.as_loop()"`

### AWS
- Do not need to install `requirements.txt`
- Just run `python -c "import setup; setup.as_lambda_function()"`
- In case you want to stop or delete the function run `sls delete`


That's it!

## Acknowledgement

Thanks to @uxDaniel and all those who have contributed to this project.

[Original repo](https://github.com/uxDaniel/visa_rescheduler)
