$versionNumber = $args[0] # get the first argument

(Get-Content "ledfx\\consts.py") -replace "CONFIG_MICRO_VERSION ", "CONFIG_MICRO__YZ_VERSION " | Set-Content "ledfx\\consts.py"

(Get-Content "ledfx\\consts.py") -replace "MICRO_VERSION = \d+", "MICRO_VERSION = $versionNumber" | Set-Content "ledfx\\consts.py"

(Get-Content "ledfx\\consts.py") -replace "CONFIG_MICRO__YZ_VERSION ", "CONFIG_MICRO_VERSION " | Set-Content "ledfx\\consts.py"

(Get-Content "pyproject.toml") -replace "version = \d+", "version = $versionNumber" | Set-Content "pyproject.toml"


