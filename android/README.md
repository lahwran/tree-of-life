build dependencies:

- java, 7 or above (`java -version` should work)
- android sdk w/ api 19 (`adb`, `android` commands on path)
- ceylon sdk (`ceylon` command on PATH - though keep in mind I hardcoded the path, build.gradle needs fixing)
- unix host (I'm lazy about making things build right on windows. feel free to fix build.gradle for win)
- build/python-install built by python-android's `./distribute.sh -d treeoflife -m "twisted parsley setuptools txws raven"`
