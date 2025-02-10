DHL custom_component
=========================

This is a custom component for home-assistant to track DHL packages.

Its activated by adding the following to your configuration.yaml:
```yaml
sensor:
  - platform: dhl
    api_key: !secret dhl_api_key
```
And you get your own api key by registering at https://developer.dhl.com/


After that you can start to track your packages by calling the service
[example register](example_register.md)
that package.

And when you loose interest in that package, you just stop tracking it by
[example unregister](example_unregister.md)


To view all your packages in a nice fashion, I use the auto-entities[1]
card to view them all as a list in lovelace:
```yaml
      - card:
          type: entities
        filter:
          include:
            - domain: sensor
              entity_id: sensor.dhl_*
        type: 'custom:auto-entities'
```

This component shares quite a bit of code and architecture
with my package tracker for Postnord[2], bring[3] and DbSchenker[4].


1. https://github.com/thomasloven/lovelace-auto-entities
2. https://github.com/glance-/postnord
3. https://github.com/glance-/bring
4. https://github.com/glance-/dbschenker
