# -*- coding: utf-8 -*- 
from troposphere import (
	Base64,
	ec2,
	GetAtt,
	Join,
	Output,
	Parameter,
	Ref,
	Template,
)

from troposphere.iam import (
	InstanceProfile,
	PolicyType as IAMPolicy,
	Role,
)

from awacs.aws import (
	Action,
	Allow,
	Policy,
	Principal,
	Statement,
)

from awacs.sts import AssumeRole

ApplicationName = "jenkins"
ApplicationPort = "8080"

GithubAccount = "Devaom"
GithubAnsibleURL = "http://github.com/{}/devops-ansible".format(GithubAccount)

AnsiblePullCmd = "/usr/local/bin/ansible-pull -U {} {}.yml -i localhost".format(GithubAnsibleURL, ApplicationName)



'''
# 동적으로 로컬의 공인IP의 Cidr를 만들어서 넣으려면 사용
from ipaddress import ip_network
from ipify import get_ip
PublicCidrIp = str(ip_network(get_ip()))
'''

t = Template()

t.add_description("Effective DevOps in AWS: HelloWorld web application")

t.add_parameter(Parameter(
	"KeyPair", # 나중에 콘솔에서 스택 생성할때 파라미터쪽에서 나타나는 필드명
	Description = "Name of an existing EC2 KeyPair to SSH",
	Type = "AWS::EC2::KeyPair::KeyName", # 이거로 지정하면 나중에 파라미터 선택할때 드롭다운으로 Key값들이 나타나게 해주는 것 같다
	ConstraintDescription = "must be the name of an existing EC2 KeyPair.",
))

t.add_resource(ec2.SecurityGroup(
	"SecurityGroup",
	GroupDescription="Allow SSH and TCP/{} access".format(ApplicationPort),
	SecurityGroupIngress=[
		ec2.SecurityGroupRule(
			IpProtocol = "tcp",
			FromPort = "22",
			ToPort = "22",
			CidrIp = "0.0.0.0/0",
			#CidrIp = PublicCidrIp, # 동적으로 로컬IP만 접속하도록 허용한다
		),
		ec2.SecurityGroupRule(
			IpProtocol = "tcp",
			FromPort = ApplicationPort,
			ToPort = ApplicationPort,
			CidrIp = "0.0.0.0/0",
		),
	],
))

# EC2의 UserData기능은 인스턴스 생성 시 정의된 스크립트를 동작하도록 한다
# UserData는 스크립트를 base64로 인코딩해서 API 호출에 추가해야한다.
'''
ud = Base64(Join('\n', [ # Join함수의 첫번째 인자값은 delimiter(구분자), 두번째는 결합될 값들
	"#!/bin/bash",
	"sudo yum install --enablerepo=epel -y nodejs",
	"wget http://bit.ly/2vESNuc -0 /home/ec2-user/helloworld.js",
	"wget http://bit.ly/2vVvT18 -0 /etc/init/helloworld.conf",
	"start helloworld"
]))
'''
ud = Base64(Join('\n', [ # Join함수의 첫번째 인자값은 delimiter(구분자), 두번째는 결합될 값들
	"#!/bin/bash",
	"yum remove java-1.7.0-openjdk -y",
	"yum install java-1.8.0-openjdk -y",
	"yum install --enablerepo=epel -y git", # 이거 없어서 내 git 레포지토리를 가져올 수가 없엇따...ㅜㅜ
	"pip install ansible",
	AnsiblePullCmd,
	"echo '*/10 * * * * root {}' > /etc/cron.d/ansible-pull".format(AnsiblePullCmd)
	]))

t.add_resource(Role(
	"Role",
	AssumeRolePolicyDocument=Policy(
		Statement=[
			Statement(
				Effect=Allow,
				Action=[AssumeRole],
				Principal=Principal("Service", ["ec2.amazonaws.com"])
			)
		]
	)
))

t.add_resource(InstanceProfile(
	"InstanceProfile",
	Path="/",
	Roles=[Ref("Role")]
))

t.add_resource(ec2.Instance(
	"instance",
	ImageId = "ami-00dc207f8ba6dc919",
	InstanceType = "t2.micro",
	SecurityGroups = [Ref("SecurityGroup")], # SecurityGroup도 Parameter처럼 Ref 가능하다
	KeyName = Ref("KeyPair"),
	UserData = ud,
	IamInstanceProfile=Ref("InstanceProfile"),
))

t.add_output(Output(
	"InstancePublicIp",
	Description = "Public IP of our instance",
	Value = GetAtt("instance", "PublicIp"), # GetAtt함수는 특정 리소스의 속성값을 반환한다
))

t.add_output(Output(
	"WebUrl",
	Description = "Application endpoint",
	Value = Join("", [
		"http://", GetAtt("instance", "PublicDnsName"),
		":", ApplicationPort
	]),
))

print(t.to_json())
