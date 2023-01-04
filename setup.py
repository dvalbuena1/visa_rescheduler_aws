import subprocess
import time

from utils import Time
from visa import VisaScheduler, Result


def as_loop():
    while 1:
        handler = VisaScheduler()
        result = handler.main()

        if result == Result.RETRY:
            time.sleep(Time.RETRY_TIME)
        elif result == Result.COOLDOWN:
            time.sleep(Time.COOLDOWN_TIME)
        elif result == Result.EXCEPTION:
            time.sleep(Time.EXCEPTION_TIME)
        else:
            break


def as_lambda_function():
    subprocess.run(["sls", "deploy"], shell=True)


if __name__ == '__main__':
    as_lambda_function()
    # lambda_handler()
