__author__= 'Abhi Gupta'

import sys
import boto3
import time
from botocore.exceptions import ClientError
import json

VERBOSE = 1


"""
This class handles deleting a VPC
"""
class VPC_Remover:
    """
    Constructor
    """
    def __init__(self, region, access_key, secret_access_key):
        self.myregion = region
        self.my_access_key = access_key
        self.my_secret_access_key = secret_access_key
        self.client = boto3.resource('ec2',
                                     aws_access_key_id=self.my_access_key,
                                     aws_secret_access_key=self.my_secret_access_key,
                                     region_name=self.myregion)
        # client is the ec2 instance created using the parameters passed to the constructor

    # Detach all the internet gateways associated with the specified VPC
    def detach_igws(self, vpc):
        this_client = boto3.client('ec2', region_name=self.myregion)
        igws = vpc.internet_gateways.all()
        if igws:
            print("List of IGWs: ", igws)
            try:
                for igw in igws:
                    print("Detaching internet gateway: ", igw.id) if (VERBOSE == 1) else ""
                    vpc.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)
                    this_client.delete_internet_gateway(DryRun=False, InternetGatewayId=igw.id)
            except ClientError as e:
                print(e)


    def delete_assocs(self, vpc):
        """
        Deleting the route table associations
        :param vpc:
        :return:
        """
        tables = vpc.route_tables.all()
        if tables:
            try:
                for table in tables:
                    for assoc in table.associations:
                        print("Deleting route table association")
                        assoc.delete()
            except ClientError as e:
                print(e)

    def delete_security_groups(self, vpc):
        """
        Deleting all the security groups associated with the VPC
        :param vpc: check for security groups in this VPC
        :return:
        """
        groups = vpc.security_groups.all()
        for group in groups:
            if group.group_name == 'main':
                continue
            else:
                try:
                    group.delete()
                except ClientError as e:
                    print(e)

    def delete_routes(self, vpc):
        """
        Delete the route tables associated with the VPC
        :param vpc:
        :return:
        """
        tables = vpc.route_tables.all()  # get all the route tables from the VPC
        for table in tables:  # iterate over tables
            routes = table.routes  # get the routes of the current table
            for route in routes:  # iterate over the routes of the current table
                if route.origin == 'CreateRoute':  # routes with this origin need to be deletedw
                    # delete the route
                    try:
                        # route.delete()
                        client = boto3.client('ec2', region_name=self.myregion)
                        client.delete_route(
                            DryRun=False,
                            RouteTableId=table.id,
                            DestinationCidrBlock=route.destination_cidr_block
                        )
                    except ClientError as e:
                        print(e)
                else:
                    continue
            # all the CreateRoute routes should have been deleted at this point
            try:
                # try to delete the table itself
                print("Deleting route table: ", table.id) if VERBOSE == 1 else ""
                table.delete()
            except ClientError as e:
                print(e)

    def delete_network_acls(self, vpc):
        """
        Deleting all the network ACLs that are associated with the vpc
        :param vpc:
        :return:
        """
        acls = vpc.network_acls.all()
        for acl in acls:
            if acl.is_default == True:
                continue
            else:
                try:
                    print("Deleting network acl: ", acl.id)
                    acl.delete()
                except ClientError as e:
                    print("Failed to delete network acl")
                    print(e)

    def delete_network_interfaces(self, vpc):
        """
        Deleting all the network interfaces associated with the VPC
        :param vpc:
        :return:
        """
        subnets = vpc.subnets.all()
        # instances = vpc.instances.all()
        # for inst in instances:
        #     if inst.state != 'terminated':
        #         inst.terminate()
        #         inst.wait_until_terminated()
        if subnets:
            for net in subnets:
                interfaces = net.network_interfaces.all()
                if interfaces:
                    for interface in interfaces:
                        try:
                            print("Detaching network interface: ", interface.id)
                            interface.detach()
                            print("Deleting network interface: ", interface.id)
                            interface.delete()
                        except ClientError as e:
                            print(e)

    def delete_subnets(self, vpc):
        subnets = vpc.subnets.all()
        if subnets:
            for subnet in subnets:
                instances = subnet.instances.all()
                for inst in instances:
                    if inst.state != 'terminated':
                        print("This subnet still has unterminated instances")
                        if inst.state != 'shutting down':
                            inst.terminate()
                        inst.wait_until_terminated()
                interfaces = subnet.network_interfaces.all()
                if interfaces is not None:
                    # print("This subnet still has network interfaces!")
                    self.check_for_running_instances(vpc=vpc)
                try:
                    subnet.delete()
                except ClientError as e:
                    print(e)

    def delete_igws(self, vpc):
        """
        Delete the internet gateways associated with the VPC
        :param vpc: VPC to delete internet gateways from
        :return:
        """
        igws = vpc.internet_gateways.all()
        if igws:
            for igw in igws:
                try:
                    print("Deleting igw: ", igw.id) if VERBOSE == 1 else ""
                    igw.delete()
                except ClientError as e:
                    print(e)


    def delete_vpc(self, vpc):
        # in this case, vpc is the vpc object found in boto3
        # this allows for us to use the boto3 methods associated with that object
        self.detach_igws(vpc)
        self.delete_assocs(vpc)
        self.delete_security_groups(vpc)
        self.delete_routes(vpc)
        self.delete_network_acls(vpc)
        self.delete_network_interfaces(vpc)
        self.delete_subnets(vpc)
        self.delete_igws(vpc)
        time.sleep(15)
        try:
            vpc.delete()
        except ClientError as e:
            # sometimes, the route table doesn't delete in time to allow the VPC to be deleted
            # running this loop ensures that the VPC is deleted
            print("Error in deleting VPC")
            print("Trying to delete the VPC again")
            self.delete_vpc(vpc)

    def get_vpc_by_name(self, vpc_id, region):
        session = boto3.Session(region_name=region)
        # myEc2 = MyEC2(self.region, self.access_key, self.secret_key)  # MyEC2 variable

        ec2 = session.resource('ec2', region)
        vpcs = ec2.vpcs.all()
        for vpc in vpcs:
            if vpc.id == vpc_id:
                return vpc


if __name__ == "__main__":
    print("Enter the ID of the VPC you want to delete: ")
    vpc_id = input()
    print("Enter the region the VPC is in: ")
    region = input()
    remover = VPC_Remover(region, "", "") # fill in your access key and secret access key in the respective variables
    vpc = remover.get_vpc_by_name(vpc_id, region)
    remover.delete_vpc(vpc)

