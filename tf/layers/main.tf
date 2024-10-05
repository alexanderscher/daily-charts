provider "aws" {
  region = "us-east-1"
}

resource "aws_lambda_layer_version" "db_layer" {
  filename            = "./zips/db_layer.zip"
  layer_name          = "db-layer"
  compatible_runtimes = ["python3.8"]
  source_code_hash    = filebase64sha256("./zips/db_layer.zip")
}


resource "aws_lambda_layer_version" "spotify_layer" {
  filename            = "./zips/spotify_layer.zip"
  layer_name          = "spotify-layer"
  compatible_runtimes = ["python3.8"]
  source_code_hash    = filebase64sha256("./zips/spotify_layer.zip")
}

resource "aws_lambda_layer_version" "utils_layer" {
  filename            = "./zips/utils_layer.zip"
  layer_name          = "utils-layer"
  compatible_runtimes = ["python3.8"]
  source_code_hash    = filebase64sha256("./zips/utils_layer.zip")
}


terraform {
  backend "s3" {
    bucket = "charts-tf-state-bucket"
    key    = "layers/terraform.tfstate"
    region = "us-east-1"
  }
}
