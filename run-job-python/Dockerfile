FROM public.ecr.aws/lambda/python:3.10

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}


# Install the specified packages
RUN pip install -r requirements.txt
#install mroptimum from git repository pip install pip install git+https://github.com/cloudmrhub-com/mroptimum.git in case it has changed
# RUN pip install git+https://github.com/cloudmrhub-com/mroptimum.git

COPY site-packages /var/lang/lib/python3.10/site-packages

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
ENV SSL_CERT_FILE /etc/ssl/certs/ca-bundle.crt

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]


