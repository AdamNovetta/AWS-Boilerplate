### Example of cross-account Lambda execution

1. Setup an IAM Role in the child child/target AWS accounts for this execution

2. Make sure the role's name is identical across all accounts!

3. Attach permissions policies to this role that the admin account needs (e.g. Administrator level permissions)

4. Setup a trust relationship policy that allows the Admin AWS account access to assume role e.g.:
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

5. Gather all child account numbers

6. Create a Lambda script with the functions you want to fun against these child accounts

7. Enter account numbers in to Lambda and cycle through them using STSAssumeRole credentials to modify the boto3 client assumptions

(*Alternatively, you can use a initiator Lambda to invoke other Lambdas, passing the STSAssumeRole credentials to the downstream Lambdas for individualized logging and process separation*)
