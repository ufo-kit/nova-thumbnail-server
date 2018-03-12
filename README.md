# Thumbnail server

This is a server that generates thumbnails from raw data sets by taking the
middle slice and performing appropriate operations. The client receives a
suitable thumbnail in JPEG format after sending a GET request on
`/<user>/<dataset id>?options`. Options are

* `size` that scales image to a maximum size in each direction
