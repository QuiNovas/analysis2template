# analysis2template
Converts and existing Amazon QuickSight analysis to a template in Terraform format.

Given the name of a QuickSight analysis, this application will create a temporary template 
from the analysis, extract that template's definition, convert it to a Terraform `aws_quicksight_template` resource,
write that resource out to `stdout`, and delete the temporary template from QuickSight.

`tempalte.tf` can then be included in a larger Terraform project and modified to be appropriately scoped, permissioned
and provisioned. Once the template is available in QuickSight it may be used to create other analysis and dashboards
using Terraform.

> Note - it is intended, although not required, that the initial analysis that the tempalte is created from be a "scratch"
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
1. The Terraform that is generated will be ugly. Format it using:
    ```bash
    terraform fmt template.tf
    ```

2. Replace the name of the `aws_quicksight_template` resource and the fields `template_id` and `name` within the resource.

3. Include the new `template.tf` in your module and start creating Quicksight analysis or dashboards from it!
