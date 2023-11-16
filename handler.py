import logging

import boto3

from utils import Result, Time
from visa import VisaScheduler

logger = logging.getLogger("Visa_Logger")


def lambda_handler(event, context):
    handler = VisaScheduler()
    response = handler.main()
    logger.info(response)

    event_arn = event["resources"][0]
    event_arn = event_arn[event_arn.rindex("/") + 1:]
    scheduler_client = boto3.client('scheduler')
    rate = Time.RETRY_TIME

    if response == Result.COOLDOWN:
        rate = Time.COOLDOWN_TIME
    elif response == Result.EXCEPTION:
        rate = Time.EXCEPTION_TIME

    response = scheduler_client.get_schedule(Name=event_arn)
    scheduler_client.update_schedule(FlexibleTimeWindow=response["FlexibleTimeWindow"], Name=event_arn,
                                     ScheduleExpression=f"rate({rate // 60} minutes)", Target=response["Target"])
