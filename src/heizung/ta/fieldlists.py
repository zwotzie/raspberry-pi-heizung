from pyblnet import BLNETDirect

fields = [
    ### ANALOG ####
    "timestamp",
    "kessel_rl",
    "kessel_ladepumpe_drehzahl",
    "kessel_betriebstemperatur",
    "speicher_ladeleitung",
    "aussentemperatur",
    "raum_rasp",
    "speicher_1_kopf",
    "speicher_2_kopf",
    "speicher_3_kopf",
    "speicher_4_mitte",
    "speicher_5_boden",
    "heizung_vl",
    "heizung_rl",
    "heizung_pumpe_drehzahl",
    "solar_strahlung",
    "solar_vl",
    "solar_ladepumpe_drehzahl",
    ### DIGITAL ####
    "d_heizung_pumpe",
    "d_kessel_ladepumpe",
    "d_kessel_freigabe",
    "d_heizung_mischer_auf",
    "d_heizung_mischer_zu",
    "d_kessel_mischer_auf",
    "d_kessel_mischer_zu",
    "d_solar_kreispumpe",
    "d_solar_ladepumpe",
    "d_solar_freigabepumpe",
]

fields_dict_analog = {
    # analog values
    "9": "kessel_rl",
    "7": "kessel_betriebstemperatur",
    "6": "speicher_ladeleitung",
    "1": "aussentemperatur",
    "8": "raum_rasp",
    "2": "speicher_1_kopf",
    "3": "speicher_2_kopf",
    "4": "speicher_3_kopf",
    "16": "speicher_4_mitte",
    "5": "speicher_5_boden",
    "10": "heizung_vl",
    "11": "heizung_rl",
    "15": "solar_strahlung",
    "13": "solar_vl",
    "14": "Freigabe-WQ1",
}

fields_dict_digital = {
    # digital values
    "2:speed": "kessel_ladepumpe_drehzahl",
    "3:speed": "heizung_pumpe_drehzahl",  # '6:speed': 'heizung_pumpe_drehzahl',
    "4:speed": "solar_ladepumpe_drehzahl",  # '7:speed': 'solar_ladepumpe_drehzahl',
    # '1': 'start_fire',
    "6": "d_heizung_pumpe",
    "2": "d_kessel_ladepumpe",
    "5": "d_kessel_freigabe",
    "10": "d_heizung_mischer_auf",
    "11": "d_heizung_mischer_zu",
    "8": "d_kessel_mischer_auf",
    "9": "d_kessel_mischer_zu",
    "4": "d_solar_kreispumpe",
    "3": "d_solar_ladepumpe",
    "7": "d_solar_freigabepumpe",
}

keys_analog_fe = [
    "Zeit",
    "RL Kessel",
    "Drehzahl Ladepumpe Kessel",
    "Kessel Betriebstemperatur",
    "Speicherladeleitung",
    "Außentemperatur",
    "Raum RASPT",
    "Speicher 1 Kopf",
    "Speicher 2 Oben",
    "Speicher 3 Unten",
    "Speicher 4 Mitte",
    "Speicher 5 Boden",
    "VL Heizung",
    "RL Heizung",
    "Drehzahl Heizungspumpe",
    "Solarstrahlung",
    "VL Solar",
    "Drehzahl Ladepumpe Solar",
]

keys_digital_fe = [
    "Heizung: Pumpe",
    "Kessel: Ladepumpe",
    "Kessel: Freigabe",
    "Hz Mischer auf",
    "Hz Mischer zu",
    "Kessel Mischer auf",
    "Kessel Mischer zu",
    "Solarkreispumpe",
    "Solar: Ladepumpe",
    "Solar: Freigabeventil",
]

api_keys = [
    "date",
    "frame",
    "analog1",
    "analog2",
    "analog3",
    "analog4",
    "analog5",
    "analog6",
    "analog7",
    "analog8",
    "analog9",
    "analog10",
    "analog11",
    "analog12",
    "analog13",
    "analog14",
    "analog15",
    "analog16",
    "digital1",
    "digital2",
    "digital3",
    "digital4",
    "digital5",
    "digital6",
    "digital7",
    "digital8",
    "digital9",
    "digital10",
    "digital11",
    "digital12",
    "digital13",
    "digital14",
    "digital15",
    "digital16",
    "speed1",
    "speed2",
    "speed3",
    "speed4",
    "power1",
    "power2",
    "energy1",
    "energy2",
]

test_values = {
    "analog": {
        1: 12.5,
        2: 69.3,
        3: 61.4,
        4: 51.5,
        5: 38.2,
        6: 65.4,
        7: 27.8,
        8: 22.4,
        9: 25.5,
        10: 24.3,
        11: 24.8,
        12: 0,
        13: 31.7,
        14: 1,
        15: 0,
        16: 48.2,
    },
    "digital": {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 0,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: 0,
        16: 0,
    },
    "speed": {},
    "energy": {},
    "power": {},
}


def get_messurements(ip: str, reset: bool = False) -> dict:
    # try:
    bld = BLNETDirect(ip, reset=reset)
    blnet = bld.get_latest()
    # print(blnet)
    data = blnet[0]
    data_time = blnet["date"]
    mapping = {}
    mapping["timestamp"] = data_time
    for key, value in data["analog"].items():
        try:
            field_name = fields_dict_analog[str(key)]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found!")

    # print("DIGITAL")
    for key, value in data["digital"].items():
        try:
            field_name = fields_dict_digital[str(key)]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found")
    # print("SPEED")
    # '2:speed': 'kessel_ladepumpe_drehzahl',
    # '6:speed': 'heizung_pumpe_drehzahl',
    # '7:speed': 'solar_ladepumpe_drehzahl',
    for key, value in data["speed"].items():
        try:
            field_name = fields_dict_digital[f"{key}:speed"]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found")
    # print(mapping)
    return mapping
