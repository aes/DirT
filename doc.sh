#!/bin/sh

( cat <<EOF ;
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <head>
    <title>DirT</title>
    <style type="text/css">
table { border-collapse: collapse; }
th { text-align: left; background: #ccc; }
th, td { padding-right: 1em; }
pre { padding: 1em; border: 2px solid #ccc; }
#whole { width: 45em; margin-left: 10em;}
    </style>
  </head>
  <body>
    <div id="whole">
EOF
  markdown_py README -x extra -s escape -o xhtml ;
  cat <<EOF
    </div>
  </body>
</html>
EOF
  ) > README.html
