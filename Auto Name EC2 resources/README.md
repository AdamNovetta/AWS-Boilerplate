#   Auto Name EC2 Resources - V1.3
#### Tags EC2 assets (AMIs/EBSs/NICs/Snaps) based on the EC2 Instance 'Name' tag
--------------------------------------------------------------------------------
## Purpose:
This will rename all EBS volumes, network interfaces, snapshots, and AMIs (owned by the account running the script) in the region:
- [x] EBS volumes:  **[ _instance-name-tag_ ]-_mount_-_point_**
- [x] Interfaces: **_instance-name-tag_**
- [x] Snapshots: **[ _instance-name-tag_ ]-_mount_-_point_**

  (or description if it's not an EC2 instance interface)
- [x] AMIs: __*AMI-Name value*__

  (required to make an image, but not auto-tagged to the 'Name' tag by Amazon)



##### TODO:
  * Add usage & setup instructions to this readme
