FROM public.ecr.aws/lambda/python:3.10

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# install git
RUN yum install -y git

# Install the specified packages
RUN pip install -r requirements.txt
# 
# Install the mroptimum-tools package
RUN pip install git+https://github.com/cloudmrhub/mroptimum-tools.git


# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
ENV SSL_CERT_FILE /etc/ssl/certs/ca-bundle.crt

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]


