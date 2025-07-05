provider "aws" {
  region = "us-west-2"
}

terraform {
  backend "s3" {
    bucket = "chadderw-tf-jenkins-automation"
    key    = "terraform.tfstate"
    region = "us-west-2"
  }
}
