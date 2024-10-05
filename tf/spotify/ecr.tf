resource "aws_ecr_repository" "spotify_charts_ecr" {
  name = "spotify-charts-ecr"
}


data "aws_ecr_image" "spotify_charts_ecr" {
  repository_name = aws_ecr_repository.spotify_charts_ecr.name
  image_tag       = "latest"
}
