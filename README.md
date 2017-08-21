# Delete_AWS_Vpc
This is one of the ways to delete a VPC in AWS. The program needs to be provided with the user's access key and secret access key to function properly.
When using boto3 to delete a VPC, the deletion steps need to be executed in a certain order if they are to successfully delete the VPC.
I've run extensive tests on this code and it successfully deletes a given VPC, as long as the VPC is not the default one for the region.