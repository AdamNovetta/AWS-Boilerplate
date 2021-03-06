## AWS Boilerplate Scripts
### Contents:
* #### Auto Name EC2 resources - **V.1.3** Python3 / Boto3
  * This Lambda script will rename all EBS volumes, network interfaces, snapshots, and AMIs (owned by the account running the script) in the region. Resources attached to an EC2 instances will get name-tags based on the instance's name-tag.

* #### Auto Start and Stop EC2 & RDS Instances - **AutoOrc V.1.2** - Python3 / Boto3
  * A Lambda script that will automatically start and stop all ec2 instances and RDS (non-multi AZ support only!) instances in your AWS account based off of start/stop tags applied to the resources.


* #### Cross Account Execution - **V.1.0** Python3 / Boto3
  * A script to query external AWS accounts (via STSAssumeRole), for remote administration. This example will read out the running EC2 instances in all included AWS accounts.


* #### EBS Snapshots - **V.2.3** Python3 / Boto3
  * A Lambda script to automatically snapshot EBS volumes and manage the retention of old automatic snapshots. Uses tags on the EBS volumes to determine the frequency of the backups for the volumes.




## AWS Boilerplate commands

* #### One liner commons
  * Common one line commands used in AWS
