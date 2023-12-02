import re
from collections.abc import Iterable, Mapping
from logging import ERROR, getLogger
from numbers import Number
from string import Template
from time import sleep
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from argh import CommandError, arg, dispatch_command, wrap_errors
from boto3 import client
from boto3.compat import filter_python_deprecation_warnings
from termcolor import colored

if TYPE_CHECKING:
    from mypy_boto3_quicksight.type_defs import (
        DataSetReferenceTypeDef,
        TemplateSourceAnalysisTypeDef,
        TemplateSourceEntityTypeDef,
    )
else:
    DataSetReferenceTypeDef = dict
    TemplateSourceAnalysisTypeDef = dict
    TemplateSourceEntityTypeDef = dict


filter_python_deprecation_warnings()

getLogger("boto3").setLevel(ERROR)

AWS_QUICKSIGHT_TEMPLATE = Template(
    """
resource "aws_quicksight_template" "example" {
  template_id = "example_id"
  name = "example_name"
  version_description = "Initial version"
  $definition
}
"""
)
CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


def escape_strings(s: str) -> str:
    if "\n" in s:
        return f"<<EOT\n{s}\nEOT"
    if '"' in s:
        s = s.replace('"', '\\"')
    return f'"{s}"'


def to_terraform(key: str, value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, Mapping):
        return (
            f'{CAMEL_TO_SNAKE.sub("_", key).lower()} {{\n'
            + "\n".join([to_terraform(k, v) for k, v in value.items()])
            + "\n}"
        )
    if isinstance(value, Iterable) and not isinstance(value, str):
        value = list(value)
        if isinstance(value[0], Mapping):
            return "\n".join([to_terraform(key, v) for v in value])
        if isinstance(value[0], str):
            return (
                f'{CAMEL_TO_SNAKE.sub("_", key).lower()} = ['
                + ",".join([f"{escape_strings(v)}" for v in value])
                + "]"
            )
        if isinstance(value[0], bool):
            return (
                f'{CAMEL_TO_SNAKE.sub("_", key).lower()} = ['
                + ",".join(["true" if v else "false" for v in value])
                + "]"
            )
        if isinstance(value[0], Number):
            return (
                f'{CAMEL_TO_SNAKE.sub("_", key).lower()} = ['
                + ",".join([v for v in value])
                + "]"
            )
        raise ValueError(f"Unknown type {type(value[0])} for {key}")
    if isinstance(value, str):
        return f'{CAMEL_TO_SNAKE.sub("_", key).lower()} = {escape_strings(value)}'
    if isinstance(value, bool):
        return (
            f'{CAMEL_TO_SNAKE.sub("_", key).lower()} = {"true" if value else "false"}'
        )
    if isinstance(value, Number):
        return f'{CAMEL_TO_SNAKE.sub("_", key).lower()} = {value}'
    raise ValueError(f"Unknown type {type(value)} for {key}")


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
                return AWS_QUICKSIGHT_TEMPLATE.substitute(
                    definition=to_terraform("Definition", template["Definition"])
                )
            finally:
                quicksight.delete_template(
                    AwsAccountId=aws_account_id, TemplateId=template_id
                )

    except Exception as error:
        raise CommandError(error)


def main():
    dispatch_command(analysis2template)
