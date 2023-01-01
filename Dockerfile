FROM umihico/aws-lambda-selenium-python:latest

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY config.ini ./
COPY visa.py ./
CMD ["visa.lambda_handler"]