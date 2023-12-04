# analysis2template
Converts an existing Amazon QuickSight analysis to a template definition in JSON format.

Given the name of a QuickSight analysis, this application will create a temporary template 
from the analysis, extract that template's definition, write that defintion out to `stdout`,
and delete the temporary template from QuickSight.

> Note - it is intended, although not required, that the initial analysis that the template is created from be a "scratch"
analysis to be deleted after the template creation.

> Note - this is built and distributed for Python 3.7 in order to be able to run in AWS CloudShell. If you choose to run
locally, you will need to ensure that you have your AWS administrator credentials loaded into your shell environment 
(e.g. - awsvault).

## Installation
```bash
pip install analysis2template
```

## Usage
You can convert a QuickSight analysis to a QuickSight template using either the
analysis ID or the analysis name (the latter is easier).

### By ID
```bash
analysis2template --i my_analysis_id > template.tf
```

### By Name
```bash
analysis2template --n "My Analysis" > template.tf
```

## Post-processing
The Terraform AWS provider's `aws_quicksight_template` resource currently does not support creating/updating
a QuickSight template from a JSON definiton. Unfortunately, the schema for the `definition` in that resource
has drifted from the AWS API for QuickSight templates. Therefore, the only way to use the output of
`analysis2template` is to use the AWS API/CLI directly.

A bash script that may be used in an [`external`](https://registry.terraform.io/providers/hashicorp/external/latest/docs/data-sources/external) data source is provided in [`create_template.sh`](https://github.com/QuiNovas/analysis2template/blob/main/create_template.sh)

### Example
```hcl
data "external" "example" {
  program = ["bash", "${path.module}/create_template.sh"]

  query = {
    template_id     = "my-template"
    definition_path = "${path.module}/my-template-definition.json"
  }
}
```

Where:
- `template_id` is the unique template-id for the template that you will be creating.
- `definition_path` is the path to the output from `analysis2template` for this template.

This data source will output a `result` that is a map of string values in the following format:
```json
{
  "Arn": "arn:aws:quicksight:us-east-1:0123456789:template/my-template",
  "TemplateId": "my-template",
  "LastUpdatedTime": "2023-12-04T23:53:29.502000+00:00",
  "CreatedTime": "2023-12-04T21:44:15.705000+00:00"
}
```
