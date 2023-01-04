from enum import Enum


class Time:
    RETRY_TIME = 60 * 10  # wait time between retries/checks for available dates: 10 minutes
    EXCEPTION_TIME = 60 * 30  # wait time when an exception occurs: 30 minutes
    COOLDOWN_TIME = 60 * 60  # wait time when temporary banned (empty list): 60 minutes


class Result(Enum):
    SUCCESS = 1
    RETRY = 2
    COOLDOWN = 3
    EXCEPTION = 4
