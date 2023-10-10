# MR Optimum app

## Buckets 
- JobsBucket - mroptimum-jobs
- ResultsBucket - mroptimum-results

## APIS

|Function| Route/Event | Description |
|---|---|---|
|QueueJobFunction  | /pipeline  | Receives a POST req, create a json file on JobsBucket |
| RunJobFunction | JobsBucket upload | make the calulation and send the results to results bucket |
| UpdateJobFunction | ResultsBucket upload | take the result zip file and update cloudmrhub |
| DataUploadFunction | /uploaddatad | upload in the cloudmrhubdata bucket |
| ReadUploadFunction | /readdatad | get user data in the cloudmrhubdata |
| UserAuthorizerFunction | APiGateway | Authprizes the users |
|---|---|---|