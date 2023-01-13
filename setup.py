import json
import os
import subprocess
import time

from utils import Time


def as_loop():
    from visa import VisaScheduler, Result
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
    data = {"retry_value": Time.RETRY_TIME // 60}
    temp_file = "json_var.json"
    with open(temp_file, "w") as write_file:
        json.dump(data, write_file, indent=4)
    subprocess.run(["sls", "deploy"], shell=True)
    os.remove(temp_file)
