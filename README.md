## AWS Boilerplate Scripts
### Contents:

* ###### Auto Start and Stop EC2 & RDS Instances - **AutoOrc v.1.2** - Python3 / Boto3
        A Lambda script that will automatically start and stop all ec2 instances and RDS (non-multi AZ support only!) instances in your AWS account based off of start/stop tags applied to the resources.


* ###### Cross Account Execution - Python3 / Boto3
        A script to query external AWS accounts (via STSAssumeRole), for remote administration. This example will read out the running EC2 instances in all included account.
