import datetime

import requests

from .blnet_conn import BLNETDirect

api_url = "xxx"
hostname = 'xxx'

fields = [
### ANALOG ####
    'timestamp',
    'kessel_rl',
    'kessel_d_ladepumpe',
    'kessel_betriebstemperatur',
    'speicher_ladeleitung',
    'aussentemperatur',
    'raum_rasp',
    'speicher_1_kopf',
    'speicher_2_kopf',
    'speicher_3_kopf',
    'speicher_4_mitte',
    'speicher_5_boden',
    'heizung_vl',
    'heizung_rl',
    'heizung_d',
    'solar_strahlung',
    'solar_vl',
    'solar_d_ladepumpe',

### DIGITAL ####
    'd_heizung_pumpe',
    'd_kessel_ladepumpe',
    'd_kessel_freigabe',
    'd_heizung_mischer_auf',
    'd_heizung_mischer_zu',
    'd_kessel_mischer_auf',
    'd_kessel_mischer_zu',
    'd_solar_kreispumpe',
    'd_solar_ladepumpe',
    'd_solar_freigabepumpe']

fields_dict_analog = {
    # analog values
    '9': 'kessel_rl',
    '7': 'kessel_betriebstemperatur',
    '6': 'speicher_ladeleitung',
    '1': 'aussentemperatur',
    '8': 'raum_rasp',
    '2': 'speicher_1_kopf',
    '3': 'speicher_2_kopf',
    '4': 'speicher_3_kopf',
    '16': 'speicher_4_mitte',
    '5': 'speicher_5_boden',
    '10': 'heizung_vl',
    '11': 'heizung_rl',
    '15': 'solar_strahlung',
    '13': 'solar_vl',
    '14': 'Freigabe-WQ1'
}

fields_dict_digital = {
    # digital values
    '2:speed': 'kessel_d_ladepumpe',
    '3:speed': 'heizung_d',  # '6:speed': 'heizung_d',
    '4:speed': 'solar_d_ladepumpe',  # '7:speed': 'solar_d_ladepumpe',
    '6': 'd_heizung_pumpe',
    '2': 'd_kessel_ladepumpe',
    '5': 'd_kessel_freigabe',
    '10': 'd_heizung_mischer_auf',
    '11': 'd_heizung_mischer_zu',
    '8': 'd_kessel_mischer_auf',
    '9': 'd_kessel_mischer_zu',
    '4': 'd_solar_kreispumpe',
    '3': 'd_solar_ladepumpe',
    '7': 'd_solar_freigabepumpe'}

keys_analog_fe = ['Zeit', 'RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur', 'Speicherladeleitung',
 'Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte',
 'Speicher 5 Boden', 'VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar']

keys_digital_fe = ['Heizung: Pumpe', 'Kessel: Ladepumpe', 'Kessel: Freigabe', 'Hz Mischer auf', 'Hz Mischer zu',
 'Kessel Mischer auf', 'Kessel Mischer zu', 'Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil']

api_keys = ["date", "frame",
            "analog1", "analog2", "analog3", "analog4", "analog5", "analog6", "analog7", "analog8",
            "analog9", "analog10", "analog11", "analog12", "analog13", "analog14", "analog15", "analog16",
            "digital1", "digital2", "digital3", "digital4", "digital5", "digital6", "digital7", "digital8",
            "digital9", "digital10", "digital11", "digital12", "digital13", "digital14", "digital15", "digital16",
            "speed1", "speed2", "speed3", "speed4",
            "power1", "power2", "energy1", "energy2"]

test_values = {
    'analog': {1: 12.5, 2: 69.3, 3: 61.4, 4: 51.5, 5: 38.2, 6: 65.4, 7: 27.8, 8: 22.4, 9: 25.5, 10: 24.3, 11: 24.8, 12: 0, 13: 31.7, 14: 1, 15: 0, 16: 48.2},
    'digital': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0},
    'speed': {},
    'energy': {},
    'power': {}
}


def get_messurements(ip: str, reset: bool=False):
    # try:
    bld = BLNETDirect(ip, reset=reset)
    blnet = bld.get_latest()
    # print(blnet)
    data = blnet[0]
    data_time = blnet['date']
    mapping = {}
    mapping['timestamp'] = data_time
    for key, value in data['analog'].items():
        try:
            field_name = fields_dict_analog[str(key)]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found!")

    # print("DIGITAL")
    for key, value in data['digital'].items():
        try:
            field_name = fields_dict_digital[str(key)]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found")
    # print("SPEED")
    # '2:speed': 'kessel_d_ladepumpe',
    # '6:speed': 'heizung_d',
    # '7:speed': 'solar_d_ladepumpe',
    for key, value in data['speed'].items():
        try:
            field_name = fields_dict_digital[f"{key}:speed"]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found")
    # print(mapping)
    field_list = [mapping[field] if field in mapping else 0 for field in fields]

    api_data = {"date": f"{data_time}", "frame": 1}
    api_data.update({f"analog{k}": v for k, v in data["analog"].items()})
    api_data.update({f"digital{k}": v for k, v in data["digital"].items()})
    api_data.update({f"speed{k}": "NULL" if v is None else v for k, v in data["speed"].items()})
    api_data.update({f"power{k}": "NULL" if v is None else v for k, v in data["power"].items()})
    api_data.update({f"energy{k}": "NULL" if v is None else v for k, v in data["energy"].items()})

    # print(field_list)
    return field_list, mapping, api_data

def fields_example():
    example = [
        1729375260,
        46.8, 0, 52.5, 76.4, 13.4, 22, 80.6, 77.6, 77.5, 76.3, 58.7, 31.4, 28.8, 0, 0, 34.3,
        0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0
    ]
    print("ANALOG")
    from blnet_parser import BLNETParser
    from blnet_conn import BLNETDirect
    import socket
    # try:
    ip = socket.gethostbyname(hostname)
    bld = BLNETDirect(ip, reset=False)
    blnet = bld.get_latest()
    print(blnet)
    data = blnet[0]
    data_time = blnet['date']
    #raise
    #except Exception as e:
    #    print(f"Exception: {e}")
    #    data = b'} \xb5"f"\x03"~!\x8e"\x16!\xe0 \xff \xf3 \xf8 \x00\x00=!\x01\x00\x00`\xe2!\x00\x00\x80\x00\x00\x00\x00,\x00\xa4(\x06\x00DhI\x82\x1d\x04Ce\xc0\x00'
    # blnet = BLNETParser(data).to_dict()
    mapping = {}
    mapping['timestamp'] = data_time
    for key, value in data['analog'].items():
        try:
            field_name = fields_dict_analog[str(key)]
            print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            print(f"{key} : {value} : not found!")

    print("DIGITAL")
    for key, value in data['digital'].items():
        try:
            field_name = fields_dict_digital[str(key)]
            print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            print(f"{key} : {value} : not found")
    print(mapping)
    field_list = [mapping[field] if field in mapping else 0 for field in fields]
    print(field_list)

def fields_example2():
    # data = b'} \xb5"f"\x03"~!\x8e"\x16!\xe0 \xff \xf3 \xf8 \x00\x00=!\x01\x00\x00`\xe2!\x00\x00\x80\x00\x00\x00\x00,\x00\xa4(\x06\x00DhI\x82\x1d\x04Ce\xc0\x00'
    # data = BLNETParser(data).to_dict()
    # print(data)
    blnet = [{
        'date': datetime.datetime.now(),
        'analog': {1: 12.5, 2: 69.3, 3: 61.4, 4: 51.5, 5: 38.2, 6: 65.4, 7: 27.8, 8: 22.4, 9: 25.5, 10: 24.3, 11: 24.8, 12: 0, 13: 31.7, 14: 1, 15: 0, 16: 48.2},
        'digital': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0},
        'speed': {}, 'energy': {}, 'power': {}
    }]
    data = blnet[0]

    data_time = data['date'].strftime("%Y-%m-%d, %H:%M:%S")
    api_data = {"date": f"{data_time}", "frame": "frame1"}
    api_data.update({f"analog{k}": v for k, v in data["analog"].items()})
    api_data.update({f"digital{k}": v for k, v in data["digital"].items()})
    api_data.update({f"speed{k}": "NULL" for k in range(1, 5)})
    api_data.update({f"power{k}": "NULL" for k in range(1, 3)})
    api_data.update({f"energy{k}": "NULL" for k in range(1, 3)})

    api_url = "xxx"
    request_url = api_url + "/databasewrapper/insertData"
    # field_list, mapping, api_data = fields_example2()
    print("api_data = ", api_data)
    result = requests.post(request_url, json=[[api_data]])
    print(f"result:      {result.text}")
    print(f"status_code: {result.status_code}")

    # for api_key in api_keys:
    #    print(f"{api_key}: {api_data[api_key]}, ")

    mapping = {}
    mapping['timestamp'] = data_time
    for key, value in data['analog'].items():
        try:
            field_name = fields_dict_analog[str(key)]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found!")

    # print("DIGITAL")
    for key, value in data['digital'].items():
        try:
            field_name = fields_dict_digital[str(key)]
            # print(f"{key} : {value} : {field_name}")
            mapping[field_name] = value
        except KeyError:
            pass
            # print(f"{key} : {value} : not found")
    print(mapping)
    field_list = [mapping[field] if field in mapping else 0 for field in fields]
    print(field_list)

    return field_list, mapping, api_data


def transfer_data_ok():
    """
    This method transfers the data from uvr1611 to the api of same project to hosting server
    """
    print('+------------------ transfer data from uvr1611 ------------------------')
    # TODO push to api
    request_url = api_url + "/databasewrapper/insertData"
    keys = ["date", "frame",
    "analog1", "analog2", "analog3", "analog4", "analog5", "analog6", "analog7", "analog8",
    "analog9", "analog10", "analog11", "analog12", "analog13", "analog14", "analog15", "analog16",
    "digital1", "digital2", "digital3", "digital4", "digital5", "digital6", "digital7", "digital8",
    "digital9", "digital10", "digital11", "digital12", "digital13", "digital14", "digital15", "digital16",
    "speed1", "speed2", "speed3", "speed4",
    "power1", "power2",
    "energy1", "energy2"]
    data = [datetime.datetime(2024, 10, 29, 23, 17, 48, 20935),
            25.4, 0, 28.7, 48.2, 11.7, 22.2, 51.6, 44.2, 43.6, 43.2, 32.8, 23.1, 23.8, 0, 0, 30.2,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,0,0,0,0,0]
    print(len(data))
    push_data = [data[0].strftime("%Y-%m-%d, %H:%M:%S"), "frame1"] + data[1:] + [0, 0, 0, 0, 0, "NULL", 0, 0]
    push_data = dict(zip(keys, push_data))
    push_data = [push_data]
    print(f"push_data: {push_data}")
    result = requests.post(request_url, json=[push_data])
    print(f"result:      {result.text}")
    print(f"status_code: {result.status_code}")

    # result = requests.get(api_url + "/databasewrapper/updateTables")
    # print(f"result: {result}")


def transfer_data():
    """
    This method transfers the data from uvr1611 to the api of same project to hosting server
    """
    print('+------------------ transfer data from uvr1611 ------------------------')
    # TODO push to api
    request_url = api_url + "/databasewrapper/insertData"
    keys = ["date", "frame",
    "analog1", "analog2", "analog3", "analog4", "analog5", "analog6", "analog7", "analog8",
    "analog9", "analog10", "analog11", "analog12", "analog13", "analog14", "analog15", "analog16",
    "digital1", "digital2", "digital3", "digital4", "digital5", "digital6", "digital7", "digital8",
    "digital9", "digital10", "digital11", "digital12", "digital13", "digital14", "digital15", "digital16",
    "speed1", "speed2", "speed3", "speed4",
    "power1", "power2", "energy1", "energy2"]
    data = [datetime.datetime(2024, 10, 29, 22, 17, 48, 20935),
            25.4, 0, 28.7, 48.2, 11.7, 22.2, 51.6, 44.2, 43.6, 43.2, 32.8, 23.1, 23.8, 0, 0, 30.2,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    print(len(data))
    push_data = [f"{data[0]}", "frame1"] + data[1:] + ["NULL"] * 8
    push_data = dict(zip(keys, push_data))
    push_data = [push_data]
    print(f"push_data: {push_data}")
    result = requests.post(request_url, json=[push_data])
    print(f"result:      {result.text}")
    print(f"status_code: {result.status_code}")

    # result = requests.get(api_url + "/databasewrapper/updateTables")
    # print(f"result: {result}")

if __name__ == "__main__":
    # transfer_data_ok()
    # exit(0)
    fields_example2()
    pass

    d1 = {'date': '2024-10-29 22:16:48.020935', 'frame': 'frame1', 'analog1': 25.4, 'analog2': 0, 'analog3': 28.7, 'analog4': 48.2, 'analog5': 11.7, 'analog6': 22.2, 'analog7': 51.6, 'analog8': 44.2, 'analog9': 43.6, 'analog10': 43.2, 'analog11': 32.8, 'analog12': 23.1, 'analog13': 23.8, 'analog14': 0, 'analog15': 0, 'analog16': 30.2, 'digital1': 0, 'digital2': 0, 'digital3': 0, 'digital4': 0, 'digital5': 0, 'digital6': 0, 'digital7': 0, 'digital8': 0, 'digital9': 0, 'digital10': 0, 'digital11': 0, 'digital12': 0, 'digital13': 0, 'digital14': 0, 'digital15': 0, 'digital16': 0, 'speed1': 0, 'speed2': 0, 'speed3': 0, 'speed4': 0, 'power1': 0, 'power2': 'NULL', 'energy1': 0, 'energy2': 0}
    d2 = {'date': '2024-10-30 07:56:33',        'frame': "frame1", 'analog1': 9.1, 'analog2': 61.1, 'analog3': 54.3, 'analog4': 49.6, 'analog5': 40.2, 'analog6': 41.6, 'analog7': 44.0, 'analog8': 22.2, 'analog9': 31.5, 'analog10': 31.2, 'analog11': 27.9, 'analog12': 0, 'analog13': 41.1, 'analog14': 1, 'analog15': 34, 'analog16': 43.7, 'digital1': 0, 'digital2': 1, 'digital3': 0, 'digital4': 0, 'digital5': 0, 'digital6': 1, 'digital7': 0, 'digital8': 1, 'digital9': 0, 'digital10': 0, 'digital11': 0, 'digital12': 0, 'digital13': 0, 'digital14': 0, 'digital15': 0, 'digital16': 0, 'speed1': 'NULL', 'speed2': 'NULL', 'speed3': 'NULL', 'speed4': 'NULL', 'energy1': 'NULL', 'energy2': 'NULL', 'power1': 'NULL', 'power2': 'NULL'}
    ok = [{'date': '2024-10-29, 23:17:48', 'frame': 'frame1', 'analog1': 25.4, 'analog2': 0,    'analog3': 28.7, 'analog4': 48.2, 'analog5': 11.7, 'analog6': 22.2, 'analog7': 51.6, 'analog8': 44.2, 'analog9': 43.6, 'analog10': 43.2, 'analog11': 32.8, 'analog12': 23.1, 'analog13': 23.8, 'analog14': 0, 'analog15': 0, 'analog16': 30.2, 'digital1': 0, 'digital2': 0, 'digital3': 0, 'digital4': 0, 'digital5': 0, 'digital6': 0, 'digital7': 0, 'digital8': 0, 'digital9': 0, 'digital10': 0, 'digital11': 0, 'digital12': 0, 'digital13': 0, 'digital14': 0, 'digital15': 0, 'digital16': 0, 'speed1': 0, 'speed2': 0, 'speed3': 0, 'speed4': 0, 'power1': 0, 'power2': 'NULL', 'energy1': 0, 'energy2': 0}]
    nk = [{'date': '2024-10-30, 09:00:19', 'frame': 'frame1', 'analog1': 12.5, 'analog2': 69.3, 'analog3': 61.4, 'analog4': 51.5, 'analog5': 38.2, 'analog6': 65.4, 'analog7': 27.8, 'analog8': 22.4, 'analog9': 25.5, 'analog10': 24.3, 'analog11': 24.8, 'analog12': 0,    'analog13': 31.7, 'analog14': 1, 'analog15': 0, 'analog16': 48.2, 'digital1': 0, 'digital2': 0, 'digital3': 0, 'digital4': 0, 'digital5': 0, 'digital6': 0, 'digital7': 0, 'digital8': 0, 'digital9': 0, 'digital10': 0, 'digital11': 0, 'digital12': 0, 'digital13': 0, 'digital14': 0, 'digital15': 0, 'digital16': 0, 'speed1': 'NULL', 'speed2': 'NULL', 'speed3': 'NULL', 'speed4': 'NULL', 'power1': 'NULL', 'power2': 'NULL', 'energy1': 'NULL', 'energy2': 'NULL'}]
