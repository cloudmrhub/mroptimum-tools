# MR Optimum app

## Buckets 
- JobsBucket - mroptimum-jobs
- ResultsBucket - mroptimum-results

## APIS

|Function| Route/Event | Description |
|---|---|---|
|QueueJobFunction  | /pipeline  | Receives a POST req, create a json file on JobsBucket |
| RunJobFunction | JobsBucket upload | Makes the calulation and send the results to results bucket |
| UpdateJobFunction | ResultsBucket upload | Takes the result zip file and update cloudmrhub |
| DataUploadFunction | /uploaddatad | Uploads in the cloudmrhubdata bucket |
| ReadUploadFunction | /readdatad | Gets user data in the cloudmrhubdata |
| UserAuthorizerFunction | APiGateway | Authorizes the users |
DeleteFileFuction | /deletedata | (GET) delete file need file_id |
updateFileFuction | /updatadata | (POST) update file{fileid:xx,filename:xxy}|


|---|---|---|

## Version
1. [ ] -- frontend
1. [x] v0y  -- uploaders
1. [x] v0 -- backend
1. [x] EB 