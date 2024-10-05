provider "aws" {
  region = "us-east-1"

}

terraform {
  backend "s3" {
    bucket = "charts-tf-state-bucket"
    key    = "spotify/terraform.tfstate"
    region = "us-east-1"
  }
}
