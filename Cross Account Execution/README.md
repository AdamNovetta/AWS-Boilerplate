### Example of cross-account Lambda execution


#### Setup
1. Setup an IAM Role in the child child/target AWS accounts for this execution

  * **Make sure this role's name is identical across all accounts**

2. Attach permissions policies to this new role that the admin account needs to operate (e.g. [Administrator level permissions](https://console.aws.amazon.com/iam/home#/policies/arn:aws:iam::aws:policy/AdministratorAccess$serviceLevelSummary) for the parent account to have full permissions in the child account)

3. Setup a trust relationship policy that allows the parent/admin AWS account access to assume role e.g.:
```json
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::$$ADMIN-AWS-ACCOUNT-NUMBER$$:root"
        },
        "Action": "sts:AssumeRole"
      }
    ]
}
```

4. Create a Lambda script with the functions you want to run against these child accounts, passing the assumed credentials to the boto3 resources your instantiating.

  In this example, the assumed credentials are getting passed to a **list_ec2_instances()** function.

  Replace or edit this function to test out different boto3 calls to the target accounts.


5. Enter account numbers in to Lambda and cycle through them using STSAssumeRole credentials to modify the boto3 client assumptions

  (*Alternatively, you could use a initiator Lambda to invoke other Lambdas, passing these STSAssumeRole credentials to the downstream Lambda's functions*)


#### About

This lambda_function.py example script will cycle through the AWS account numbers in this list:
```python
  AWSChildAccounts = [
    # your aws account numbers
    '1234567890',
    '0987654321'
  ]
```
On successfully connecting to the child account this script will print out the running ec2 instances from each of the accounts.
