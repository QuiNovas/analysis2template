from argh import arg, dispatch_command, wrap_errors, CommandError
from termcolor import colored
from boto3 import client
from boto3.compat import filter_python_deprecation_warnings
from logging import getLogger, ERROR
import json
from typing import TYPE_CHECKING
from time import sleep
from uuid import uuid4

if TYPE_CHECKING:
    from mypy_boto3_quicksight.type_defs import (
        TemplateSourceEntityTypeDef,
        TemplateSourceAnalysisTypeDef,
        DataSetReferenceTypeDef,
    )
else:
    DataSetReferenceTypeDef = dict
    TemplateSourceAnalysisTypeDef = dict
    TemplateSourceEntityTypeDef = dict



filter_python_deprecation_warnings()

getLogger('boto3').setLevel(ERROR)

def main():
    dispatch_command(analysis2template)


@wrap_errors(processor=lambda err: colored(str(err), "red"))
@arg("--i", help="The Quicksight ID of the analysis to use to create the template.")
@arg("--n", help="The name of the analysis to use to create the tmeplate.")
def analysis2template(
    i: str = None,
    n: str = None,
) -> None:
    if i and n:
        raise CommandError("i and n are mutually exclusive")
    if not (i or n):
        raise CommandError("You must supply i or n")
    analysis_id = i
    analysis_name = n
    try:
        aws_account_id = client("sts").get_caller_identity()["Account"]
        quicksight = client("quicksight")
        if analysis_name:
            params = dict(AwsAccountId=aws_account_id)
            while True:
                analyses = quicksight.list_analyses(**params)
                for analysis_summary in analyses["AnalysisSummaryList"]:
                    if analysis_name == analysis_summary["Name"]:
                        analysis_id = analysis_summary["AnalysisId"]
                        break
                if i or not analyses.get("NextToken"):
                    break
                params["NextToken"] = analyses["NextToken"]
            if not analysis_id:
                raise CommandError(f"Analyis {n} not found")
            analysis = quicksight.describe_analysis(
                AwsAccountId=aws_account_id, AnalysisId=analysis_id
            )
            analysis_definition = quicksight.describe_analysis_definition(
                AwsAccountId=aws_account_id, AnalysisId=analysis_id
            )
            template_id = str(uuid4())
            quicksight.create_template(
                AwsAccountId=aws_account_id,
                TemplateId=template_id,
                SourceEntity=TemplateSourceEntityTypeDef(
                    SourceAnalysis=TemplateSourceAnalysisTypeDef(
                        Arn=analysis["Analysis"]["Arn"],
                        DataSetReferences=[
                            DataSetReferenceTypeDef(
                                DataSetPlaceholder=dataset["Identifier"],
                                DataSetArn=dataset["DataSetArn"],
                            )
                            for dataset in analysis_definition["Definition"][
                                "DataSetIdentifierDeclarations"
                            ]
                        ],
                    )
                ),
            )
            try:
                while True:
                    status = quicksight.describe_template(
                        AwsAccountId=aws_account_id, TemplateId=template_id
                    )["Template"]["Version"]["Status"]
                    if status in ("CREATION_FAILED", "UPDATE_FAILED", "DELETED"):
                        raise RuntimeError(
                            f"Unable to create intermediate template: {status}"
                        )
                    if status in ("CREATION_IN_PROGRESS", "UPDATE_IN_PROGRESS"):
                        sleep(5)
                        continue
                    break
                template = quicksight.describe_template_definition(
                    AwsAccountId=aws_account_id, TemplateId=template_id
                )
                yield json.dumps(template, indent=2)
            finally:
                quicksight.delete_template(
                    AwsAccountId=aws_account_id, TemplateId=template_id
                )

    except Exception as error:
        raise CommandError(error)

