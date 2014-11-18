build dependencies:

- java, 7 or above (`java -version` should work)
- android sdk w/ api 19 (`adb`, `android`, etc commands on path)
- `ceylon` command on PATH - http://ceylon-lang.org/download/
- unix host (I'm lazy about making things build right on windows. feel free to fix build.gradle for win)
- build/python-install built by python-android's `./distribute.sh -d treeoflife -m "openssl pyopenssl twisted parsley py setuptools txws raven"`
- **MAKE SURE YOUR python-android is up to date** before building, because you DO NOT WANT TO USE openssl older than 1.0.1g because heartbleed
