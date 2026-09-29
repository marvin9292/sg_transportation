# SG Transportation

A Home Assistant custom integration for Singapore public transport data from the LTA DataMall API.

## Features

- Bus arrival sensors for selected bus stop and service combinations.
- Train service alert sensors for Singapore MRT/LRT lines.
- Home Assistant Config Flow and Config Subentries.
- LTA DataMall `AccountKey` is entered in Home Assistant and is not stored in this repository.

## Requirements

You need your own LTA DataMall API `AccountKey`. Register for API access at the official LTA DataMall website:

https://datamall.lta.gov.sg/content/datamall/en/request-for-api.html

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/marvin9292/sg_transportation` as a custom repository with category **Integration**.
3. Download **SG Transportation** in HACS.
4. Restart Home Assistant when HACS asks you to.
5. Go to **Settings > Devices & services > Add Integration** and select **SG Transportation**.
6. Enter your own LTA DataMall `AccountKey`.

If SG Transportation was already installed manually, HACS can manage the same `custom_components/sg_transportation` directory after the repository is added and downloaded. Keep the existing Home Assistant config entry so existing subentries and entity identifiers are preserved.

## Updating the AccountKey

Open **Settings > Devices & services > SG Transportation** and use the integration's reconfigure/reauthentication flow when required.

## Data source

This integration uses Singapore Land Transport Authority (LTA) DataMall APIs. It is an independent Home Assistant custom integration and is not affiliated with or endorsed by LTA or Home Assistant.

## Privacy and credentials

Your LTA DataMall `AccountKey` is stored in your Home Assistant config entry. Do not publish it in GitHub issues, logs, screenshots, or source files.

## Support

Report integration problems through GitHub Issues:

https://github.com/marvin9292/sg_transportation/issues
