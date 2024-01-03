(Get-Content "ledfx\\consts.py") -replace "CONFIG_MICRO_VERSION ", "CONFIG_MICRO__YZ_VERSION " | Set-Content "ledfx\\consts.py"

(Get-Content "ledfx\\consts.py") -replace "MICRO_VERSION = \d+", "MICRO_VERSION = $args" | Set-Content "ledfx\\consts.py"

(Get-Content "ledfx\\consts.py") -replace "CONFIG_MICRO__YZ_VERSION ", "CONFIG_MICRO_VERSION " | Set-Content "ledfx\\consts.py"
