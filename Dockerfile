FROM umihico/aws-lambda-selenium-python:latest

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY config.ini ./
COPY utils.py ./
COPY visa.py ./
COPY handler.py ./
CMD ["handler.lambda_handler"]