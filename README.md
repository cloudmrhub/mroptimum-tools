
# MR Optimum Backend

This repository contains the backend services for **MR Optimum**, responsible for managing the computational task of the SNR

---

## Table of Contents

1. [Overview](#overview)
1. [Templates Workflow](#templates-workflow)
1. [Setup Instructions](#setup-instructions)
1. [License](#license)

---

## Overview

The Repo deploys:
- Run, task, update lambda function.
- Lambda layers.
- Frontend on Amplify.
- ApiGateway, ApiGateway UsagePlan

---

## Setup Instructions

### Prerequisites

- **Python**: Version 3.8+
- **Docker**: For containerized deployment.
- **AWS CLI**: To deploy templates.
- **jq**: To read json files
- **AWS SAM**: To 

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/mr-optimum-backend.git
   cd mr-optimum-backend
   ```

1. Configure AWS CLI:
   ```bash
   aws configure
   ```

1. set the gittoken function ()

1. Deploy templates:
   ```bash
   bash setup.sh
   ```

---

## License

This project is licensed under the [MIT License](LICENSE).

---




## Versions
- dev nighly version
- v1.1 backend and frontend spin from setup.sh
- v1 backend separated from front end, only backend




[*Dr. Eros Montin, PhD*]\
(http://me.biodimensional.com)\
**46&2 just ahead of me!**








