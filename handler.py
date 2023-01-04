import boto3

from utils import Result, Time
from visa import VisaScheduler


def lambda_handler(event, context):
    handler = VisaScheduler()
    response = handler.main()
    print(response)

    event_arn = event["resources"][0]
    event_arn = event_arn[event_arn.rindex("/") + 1:]
    events_client = boto3.client('events')
    rate = Time.RETRY_TIME

    if response == Result.COOLDOWN:
        rate = Time.COOLDOWN_TIME
    elif response == Result.EXCEPTION:
        rate = Time.EXCEPTION_TIME

    events_client.put_rule(Name=event_arn,
                           ScheduleExpression=f"rate({rate // 60} minutes)")
