# Mopidy

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Component to integrate with [mopidy][Mopidy]._

**This component will set up the following platforms.**

Platform | Description
-- | --
`media_player` | Media player component that can control Mopidy.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `blueprint`.
4. Download _all_ the files from the `custom_components/mopidy/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Mopidy"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/mopidy/__init__.py
custom_components/mopidy/manifest.json
custom_components/mopidy/media_player.py
custom_components/mopidy/services.yaml
```

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[mopidy]: https://mopidy.com
[commits-shield]: https://img.shields.io/github/commit-activity/y/abates/homeassistant-mopidy.svg?style=for-the-badge
[commits]: https://github.com/abates/homeassistant-mopidy/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/abates/homeassistant-mopidy.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/custom-components/blueprint.svg?style=for-the-badge
[releases]: https://github.com/custom-components/blueprint/releases
