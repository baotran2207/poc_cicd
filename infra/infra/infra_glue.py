from os.path import dirname, abspath, join

from aws_cdk import (
    Stack,
    aws_codebuild as build_,
    aws_codecommit as code_,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codepipeline as codepipeline_,
    Duration,
)

import  aws_cdk.aws_glue_alpha as glue_ ## let use alpha version for Job class
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep
from constructs import Construct

PROJECT_NAME = "PipelinePoc"


CODE_BUILD = {
    "version": "0.2",
    "phases": {
        "install": {
            "runtime-versions": {
                "python": "latest",
                "nodejs": "latest",
            },
            "commands": [
                "python --version",
                "pip --version",
                "pip3 --version",
                "pip install poetry",
                "poetry install",
            ]
        },
        "pre_build":  {
            "commands": [
                "echo 'prebuild'",
                "poetry run pytest -s tests"
            ]
        },
        "build": {
            "commands": [
                "echo 'building' ",
            ]
        },
        "post_build": {
            "commands": [
                "echo 'Done' ",
            ]
        },
    },
    "cache": {"paths": ["/root/cachedir/**/*"]},
}

CUR_DIR = dirname(dirname(dirname(abspath(__file__))))
SCRIPTS_PATH = join(CUR_DIR, 'poc', 'gluescripts')
REPO_ARN = "arn:aws:codecommit:ap-east-1:964372540223:poc_cicd" ## from env file
glue_script_name="glue_poc_pipeline.py"

class GluePocPipeline(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket_main = s3.Bucket(
            self, f"{PROJECT_NAME}_bucket_id", bucket_name=f"{PROJECT_NAME.lower()}-dev"
        )

        s3deploy.BucketDeployment(
            self,
            f"{PROJECT_NAME}_s3deploy",
            sources=[s3deploy.Source.asset(SCRIPTS_PATH)],
            destination_bucket=bucket_main,
            destination_key_prefix="gluescripts",
        )

        main_repo = code_.Repository.from_repository_arn(
            self, id=f"{PROJECT_NAME}_precreated_repo", repository_arn=REPO_ARN
        )
        repo = code_.Repository(
            self,
            f"{PROJECT_NAME}_repo_id",
            repository_name=f"{PROJECT_NAME}_repo",
            description="Example pipeline",
        )


        # pipeline for development - new scripts which glue/lambda will read , unittest , etc  ! Not relates to infra services (non-infra folder ? )
        pipeline = codepipeline_.Pipeline(
            self,
            f"{PROJECT_NAME}_pipeline_id",
            pipeline_name=f"{PROJECT_NAME}-codepipeline-name",
        )

        codebuild_pipeline = build_.PipelineProject(
            self,
             f"{PROJECT_NAME}_codebuild_pipeline",
            environment=build_.BuildEnvironment(
                build_image=build_.LinuxBuildImage.STANDARD_6_0, ## python ver 3.10
                compute_type=build_.ComputeType.SMALL,
            ),
            # environment_variables={
            #     "Env": "dev",
            #     "username": "password",
            # },
            build_spec=build_.BuildSpec.from_object_to_yaml(CODE_BUILD),
            timeout=Duration.minutes(30)
        )
        source_output = codepipeline_.Artifact()

        pipeline.add_stage(
                stage_name="Source",
                actions=[
                    codepipeline_actions.CodeCommitSourceAction(
                        action_name="CodeCommit-Source",
                        repository=main_repo,
                        branch="master",
                        output=source_output,
                    )
                ],
            )

        pipeline.add_stage(
            stage_name="Build-Test",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="Build-Test",
                    project=codebuild_pipeline,
                    input=source_output,
                    # outputs=[build_output],
                )
            ],
        )

        ## CDK pipeline - everything relates to infrastructure such as create/update services in aws (infra folder ?)
        pipeline = CodePipeline(
            self,
            f"{PROJECT_NAME}_cdk_pipeline",
            pipeline_name=f"{PROJECT_NAME}-cdk-pipeline",
            synth=ShellStep(
                "Synth",
                input=CodePipelineSource.code_commit(
                    repository=main_repo, branch="master"
                ),
                commands=[
                    "npm install -g aws-cdk",
		            "cd infra",
                    "pip install -r requirements.txt",
                    "cdk synth",
                ],
            ),
        )

        ## glue
        simple_glue_job = self._create_glue(
            job_name=f"simple-glue",
            s3_bucket=bucket_main,
            s3_key=f"gluescripts/{glue_script_name}"
        )

    def _create_glue(self, job_name: str, s3_bucket: s3.Bucket,s3_key: str) -> glue_.Job:
        glue_job = glue_.Job(self, f"{PROJECT_NAME}-{job_name}-id",
            executable=glue_.JobExecutable.python_shell(
                glue_version=glue_.GlueVersion.V1_0,
                python_version=glue_.PythonVersion.THREE,
                script=glue_.Code.from_bucket(s3_bucket, s3_key)
            ),
            job_name=job_name,
            description="an example Python Shell job"
        )
        return glue_job
        # snyk_build_project.add_to_role_policy(iam.PolicyStatement(
        #     actions=['ssm:GetParameters'],
        #     effect = iam.Effect.ALLOW,
        #     resources= [
        #                 'arn:aws:ssm:{}:{}:parameter/{}'.format(region,account,props['snyk-auth-code']),
        #                 'arn:aws:ssm:{}:{}:parameter/{}'.format(region,account,props['snyk-org-id'])
        #                 ]
        # ))
