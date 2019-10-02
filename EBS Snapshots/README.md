# AutoSnapShot - v2.3
Auto snapshot AWS EC2 EBS volumes in the current region

## Usage
Add tags to your EBS volumes for:
* DailySnapshot
* WeeklySnapshot
* MonthlySnapshot

And enter '**True**' in the tag value for any EBS volume you'd like to backup at that interval.

Modify the values for KeepDay/KeepWeek/KeepMonth to suit your retention needs:
```python
    # Number of copies to keep snapshot types
    KeepWeek = 3
    KeepDay = 5
    KeepMonth = 2
```
The defaults above will keep 3 copies of the WeeklySnapshot, 5 copies of the DailySnapshot, and 2 copies of MonthlySnapshot. As soon as a new snapshot is made the script will purge the snapshots that exceed these numbers. These snaps are individual and deleting a daily snapshot won't affect a weekly/monthly etc.

Finally, setup an SNS topic name for the email reports that this script will send.
```python
    if os.environ['SNS_TOPIC']:
        TopicName = os.environ['SNS_TOPIC']
    else:
        TopicName = 'auto-snapshots'
```
Put the SNS topic as an environment variable in the lambda config as : **SNS_TOPIC** with your topic name as the value, or change the above line in the script TopicName = '*your-topic-name*'


#### Lambda Settings:
  * Function name: ***AutoSnapShot*** (or whatever you'd like to call this)
  * Runtime : ***Python 3.7***
  * Handler : ***lambda_function.lambda_handler***
  * Memory : ***512 MB***
  * Timeout : ***2-5 Min depending on how many volumes you regularly backup***
  * Description : ***AutoSnapShot EBS volumes***


#### IAM policy permissions needed
*  sns:Publish
*  ec2:CreateSnapshot
*  ec2:CreateTags
*  ec2:DeleteSnapshot
*  ec2:DescribeAvailabilityZones
*  ec2:DescribeSnapshots
*  ec2:DescribeTags
*  ec2:DescribeVolumeAttribute
*  ec2:DescribeVolumeStatus
*  ec2:DescribeVolumes
