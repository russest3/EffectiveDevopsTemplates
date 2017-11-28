"""Generating CloudFormation template."""

from awacs.aws import (
    Allow,
    Policy,
    Principal,
    Statement
)

from awacs.sts import AssumeRole

from troposphere import (
    Join,
    Ref,
    Template
)

from troposphere.codebuild import (
    Artifacts,
    Environment,
    Project,
    Source
)
from troposphere.iam import Role

t = Template()

t.add_description("Effective DevOps in AWS: CodeBuild - Helloworld container")

t.add_resource(Role(
    "ServiceRole",
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[AssumeRole],
                Principal=Principal("Service", ["codebuild.amazonaws.com"])
            )
        ]
    ),
    Path="/",
    ManagedPolicyArns=[
        'arn:aws:iam::aws:policy/AWSCodePipelineReadOnlyAccess',
        'arn:aws:iam::aws:policy/AWSCodeBuildDeveloperAccess',
        'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser',
        'arn:aws:iam::aws:policy/AmazonS3FullAccess',
        'arn:aws:iam::aws:policy/CloudWatchLogsFullAccess'
    ]
))

environment = Environment(
    ComputeType='BUILD_GENERAL1_SMALL',
    Image='aws/codebuild/docker:1.12.1',
    Type='LINUX_CONTAINER',
    EnvironmentVariables=[
        {'Name': 'REPOSITORY_NAME', 'Value': 'helloworld'},
        {'Name': 'REPOSITORY_URI',
            'Value': Join("", [
                Ref("AWS::AccountId"),
                ".dkr.ecr.",
                Ref("AWS::Region"),
                ".amazonaws.com",
                "/",
                "helloworld"])},
    ],
)

buildspec = """version: 0.2
phases:
  pre_build:
    commands:
      - apt-get -y install unzip curl
      - curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
      - unzip awscli-bundle.zip
      - ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
      - echo "da4c0be6-81f4-413f-bb15-e7dd5cf29f4f" > /tmp/execution_id.txt
      - aws codepipeline get-pipeline-execution --pipeline-name "helloworld-codepipeline-HelloWorldPipeline-1WB7IKJB8OTRM" --pipeline-execution-id $(cat /tmp/execution_id.txt) --query 'pipelineExecution.artifactRevisions[0].revisionId' --output=text > /tmp/tag.txt
      - printf "%s:%s" "713832673520.dkr.ecr.us-east-1.amazonaws.com/helloworld" "$(cat /tmp/tag.txt)" > /tmp/build_tag.txt
      - printf '{"tag":"%s"}' "$(cat /tmp/tag.txt)" > /tmp/build.json
      - $(aws ecr get-login)
  build:
    commands:
      - docker build -t "$(cat /tmp/build_tag.txt)" .
  post_build:
    commands:
      - docker push "$(cat /tmp/build_tag.txt)"
      - aws ecr batch-get-image --repository-name helloworld --image-ids imageTag="$(cat /tmp/tag.txt)" --query 'images[].imageManifest' --output text | tee /tmp/latest_manifest.json
      - aws ecr put-image --repository-name helloworld --image-tag latest --image-manifest "$(cat /tmp/latest_manifest.json)"
artifacts:
  files: /tmp/build.json
  discard-paths: yes
"""

t.add_resource(Project(
    "CodeBuild",
    Name='HelloWorldContainer',
    Environment=environment,
    ServiceRole=Ref("ServiceRole"),
    Source=Source(
        Type="CODEPIPELINE",
        BuildSpec=buildspec
    ),
    Artifacts=Artifacts(
        Type="CODEPIPELINE",
        Name="output"
    ),
))

print(t.to_json())
