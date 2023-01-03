import time
import subprocess

import boto3

from visa import VisaScheduler, Result

RETRY_TIME = 60 * 10  # wait time between retries/checks for available dates: 10 minutes
EXCEPTION_TIME = 60 * 30  # wait time when an exception occurs: 30 minutes
COOLDOWN_TIME = 60 * 60  # wait time when temporary banned (empty list): 60 minutes


def as_loop():
    while 1:
        handler = VisaScheduler()
        result = handler.main()

        if result == Result.RETRY:
            time.sleep(RETRY_TIME)
        elif result == Result.COOLDOWN:
            time.sleep(COOLDOWN_TIME)
        elif result == Result.EXCEPTION:
            time.sleep(EXCEPTION_TIME)
        else:
            break


def as_lambda_function():
    subprocess.run(["sls", "deploy"], shell=True)
    function_name = subprocess.check_output(["sls", "info"], shell=True).decode('utf-8')
    function_name = function_name[function_name.rindex(":") + 1:].strip()
    lambda_client = boto3.client('lambda')
    data_lambda = lambda_client.get_function(FunctionName=function_name)

    # EventBridge
    events_client = boto3.client('events')
    rule = events_client.put_rule(Name="visa-rescheduler-event",
                                  ScheduleExpression=f"rate({RETRY_TIME // 60} minutes)",
                                  State='ENABLED',
                                  Description="Trigger a lambda function to reschedule a visa appointment")
    events_client.put_targets(Rule="visa-rescheduler-event", Targets=[{
        "Id": "VisaReschedulerLambda",
        "Arn": data_lambda["Configuration"]["FunctionArn"]
    }])

    # Permission
    try:
        lambda_client.add_permission(Action='lambda:InvokeFunction',
                                     FunctionName=data_lambda["Configuration"]["FunctionArn"],
                                     Principal='events.amazonaws.com',
                                     SourceArn=rule["RuleArn"],
                                     StatementId='InvokeLambdaFunction')
    except lambda_client.exceptions.ResourceConflictException:
        pass


if __name__ == '__main__':
    as_lambda_function()
