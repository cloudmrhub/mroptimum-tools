# MR Optimum app

## Buckets 
- JobsBucket - mroptimum-jobs
- ResultsBucket - mroptimum-results

## APIS

|Function| Route/Event | Description |
|---|---|---|
|QueueJobFunction  | /pipeline  | Receives a POST req, create a json file on JobsBucket |
| RunJobFunction | JobsBucket upload | make the calulation and send the results to results bucket |
| updateJobFunction | ResultsBucket upload | take the result zip file and update cloudmrhub |
