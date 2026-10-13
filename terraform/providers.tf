# Credentials come from the environment or an AWS profile, never from files in
# this repository. With real AWS:  export AWS_PROFILE=<your profile>
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}
