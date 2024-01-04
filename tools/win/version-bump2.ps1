$versionNumber = $args[0] # get the first argument

(Get-Content "ledfx\\consts.py") -replace "PROJECT_VERSION = \d+", "PROJECT_VERSION = $versionNumber" | Set-Content "ledfx\\consts.py"

(Get-Content "pyproject.toml") -replace "version = \d+", "version = $versionNumber" | Set-Content "pyproject.toml"



