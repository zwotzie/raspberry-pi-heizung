# Raspberry Pi steuert Heizungsanforderung

* don't forget to "chmod 755 heizung.py" so that the programm is executable

To run the program as a "daemon", I decided to use 
supervisor http://supervisord.org. The advantages are awesome: 

* supervisord will start the program automatically - also after reboot 
* take care of restart, if the script exited unexpected!

# GpIO
Gpio 23 closes the Relais which starts the wooden fire heating.

# Acknowledgment

Thanks to Erik Bartmann for his inspiring Book "Die elektronische Welt mit Raspberry Pi entdecken"
```
19-01-26 00:02:24.663  INFO     aussentemperatur          : 1.6
19-01-26 00:02:24.665  INFO     d_heizung_mischer_auf     : 0
19-01-26 00:02:24.667  INFO     d_heizung_mischer_zu      : 0
19-01-26 00:02:24.669  INFO     d_heizung_pumpe           : 1
19-01-26 00:02:24.671  INFO     d_kessel_freigabe         : 0
19-01-26 00:02:24.673  INFO     d_kessel_ladepumpe        : 0
19-01-26 00:02:24.674  INFO     d_kessel_mischer_auf      : 0
19-01-26 00:02:24.676  INFO     d_kessel_mischer_zu       : 0
19-01-26 00:02:24.678  INFO     d_solar_freigabepumpe     : 0
19-01-26 00:02:24.680  INFO     d_solar_kreispumpe        : 0
19-01-26 00:02:24.682  INFO     d_solar_ladepumpe         : 0
19-01-26 00:02:24.684  INFO     heizung_d                 : 30
19-01-26 00:02:24.686  INFO     heizung_rl                : 26.6
19-01-26 00:02:24.688  INFO     heizung_vl                : 29.4
19-01-26 00:02:24.690  INFO     kessel_betriebstemperatur : 36.6
19-01-26 00:02:24.692  INFO     kessel_d_ladepumpe        : 0
19-01-26 00:02:24.694  INFO     kessel_rl                 : 27.7
19-01-26 00:02:24.696  INFO     raum_rasp                 : 20.3
19-01-26 00:02:24.698  INFO     solar_d_ladepumpe         : 0
19-01-26 00:02:24.699  INFO     solar_strahlung           : 0
19-01-26 00:02:24.701  INFO     solar_vl                  : 34
19-01-26 00:02:24.703  INFO     speicher_1_kopf           : 75.2
19-01-26 00:02:24.705  INFO     speicher_2_kopf           : 69
19-01-26 00:02:24.707  INFO     speicher_3_kopf           : 37.8
19-01-26 00:02:24.709  INFO     speicher_4_mitte          : 26.5
19-01-26 00:02:24.711  INFO     speicher_5_boden          : 26.3
19-01-26 00:02:24.712  INFO     speicher_ladeleitung      : 31.9
19-01-26 00:02:24.714  INFO     timestamp                 : 1548457290
19-01-26 00:02:24.716  INFO     datetime                  : 2019-01-26 00:01:30
```