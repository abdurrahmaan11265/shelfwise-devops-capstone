# Only used when no AWS account is available. Copy this file into terraform/
# and Terraform merges it over providers.tf, sending every API call to a local
# Moto AWS emulator on port 5055 instead of amazonaws.com. Delete it to go back
# to real AWS. The resources in vpc.tf and eks.tf are unchanged either way.
provider "aws" {
  region     = var.region
  access_key = "testing"
  secret_key = "testing"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    ec2 = "http://localhost:5055"
    eks = "http://localhost:5055"
    iam = "http://localhost:5055"
    sts = "http://localhost:5055"
  }
}
