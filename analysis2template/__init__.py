from argh import arg, dispatch_command, wrap_errors, CommandError
from termcolor import colored
from boto3 import client
from boto3.compat import filter_python_deprecation_warnings
from logging import getLogger, ERROR
import json

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
            params = dict(
                AwsAccountId=aws_account_id
            )
            while True:
                response = quicksight.list_analyses(**params)
                for analysis_summary in response["AnalysisSummaryList"]:
                    if analysis_name == analysis_summary["Name"]:
                        analysis_id = analysis_summary["AnalysisId"]
                        break
                if i or not response.get("NextToken"):
                    break
                params["NextToken"] = response["NextToken"]
            if not analysis_id:
                raise CommandError(f"Analyis {n} not found")
            response = quicksight.describe_analysis_definition(AwsAccountId=aws_account_id, AnalysisId=analysis_id)
            yield json.dumps(response, indent=2)

    except Exception as error:
        raise CommandError(error)
