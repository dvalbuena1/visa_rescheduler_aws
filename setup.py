import time

from visa import VisaScheduler, Result

RETRY_TIME = 60 * 10  # wait time between retries/checks for available dates: 10 minutes
EXCEPTION_TIME = 60 * 30  # wait time when an exception occurs: 30 minutes
COOLDOWN_TIME = 60 * 60  # wait time when temporary banned (empty list): 60 minutes


def as_loop():
    while 1:
        handler = VisaScheduler()
        result = handler.main()

        match result:
            case Result.SUCCESS:
                break
            case Result.RETRY:
                time.sleep(RETRY_TIME)
            case Result.COOLDOWN:
                time.sleep(COOLDOWN_TIME)
            case Result.EXCEPTION:
                time.sleep(EXCEPTION_TIME)


if __name__ == '__main__':
    h = VisaScheduler()
    h.main()
