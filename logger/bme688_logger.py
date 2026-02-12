# Modified from https://github.com/electro-dan/PiZero_Air_Quality_Meter/blob/main/airqread.py
import sys
import logging
import threading
import datetime
import schedule
import time
import MySQLdb
from pathlib import Path
from bme68x import BME68X
from time import sleep
import bme68xConstants as cnst
import bsecConstants as bsec

logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger()
client = None

with open("password.txt", "r") as f:
    pwd = f.read();
    usr = "db_user"
    db = "bme688_telemetry"
    client = MySQLdb.connect(host="localhost", user=usr, password=pwd.rstrip(), database=db)

cur = client.cursor()

bme688_state_file = "state_bme688.txt"

g_bme688_bsec_data = {}

def read_bme688_config_file(config_file_name):
    state_file_path = str(Path(__file__).resolve().parent.joinpath(config_file_name))
    state_file = open(state_file_path, "r")
    state_str = state_file.read()[1:-1]
    state_list = state_str.split(",")
    state_ints = [int(x) for x in state_list]
    return (state_ints)

def bme688_setup():
    temp_prof = [320, 100, 100, 100, 200, 200, 200, 320, 320, 320]
    dur_prof = [5, 2, 10, 30, 5, 5, 5, 5, 5, 5]
    bme = BME68X(cnst.BME68X_I2C_ADDR_LOW, 0)
    logging.debug(bme.set_heatr_conf(cnst.BME68X_ENABLE, temp_prof, dur_prof, cnst.BME68X_PARALLEL_MODE))
    sleep(0.1)
    state_ints = read_bme688_config_file(bme688_state_file)
    logging.debug(bme.set_bsec_state(state_ints))
    logging.debug("Config set....")
    logging.debug(bme.set_sample_rate(bsec.BSEC_SAMPLE_RATE_LP))
    logging.debug("Rate Set")
    return bme

def bme688_get_data(sensor):
    data = {}
    try:
        data = sensor.get_bsec_data()
    except Exception as e:
        logging.error(e)
        return None
    if data == None or data == {}:
        sleep(0.1)
        return None
    else:
        sleep(3)
        return data

def bme688_read():
    global g_bme688_bsec_data
    try:
        logging.debug("Read BME688")
        bsec_data = bme688_get_data(bme)
        tries = 0
        while bsec_data == None:
            bsec_data = bme688_get_data(bme)
            tries += 1
            if tries > 300:
                raise Exception("No data retrieved from BME688")

        logging.debug(f"BME688 out: {bsec_data}")
        g_bme688_bsec_data = bsec_data
    except Exception as e:
        logging.error(e)

def bme688_thread():
    while True:
        bme688_read()
        sleep(1)

def write_to_db():
    if g_bme688_bsec_data is None:
        return
    try:
        logging.info("Write to database")
        result = cur.execute("""INSERT INTO time_series (
        timestamp,
        iaq,
        iaq_accuracy,
        static_iaq,
        static_iaq_accuracy,
        co2_equivalent,
        co2_accuracy,
        breath_voc_equivalent,
        breath_voc_accuracy,
        raw_temperature,
        raw_pressure,
        raw_humidity,
        raw_gas,
        stabilization_status,
        run_in_status,
        temperature,
        humidity,
        gas_percentage,
        gas_percentage_accuracy
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        g_bme688_bsec_data["iaq"],
        g_bme688_bsec_data["iaq_accuracy"],
        g_bme688_bsec_data["static_iaq"],
        g_bme688_bsec_data["static_iaq_accuracy"],
        g_bme688_bsec_data["co2_equivalent"],
        g_bme688_bsec_data["co2_accuracy"],
        g_bme688_bsec_data["breath_voc_equivalent"],
        g_bme688_bsec_data["breath_voc_accuracy"],
        g_bme688_bsec_data["raw_temperature"],
        g_bme688_bsec_data["raw_pressure"],
        g_bme688_bsec_data["raw_humidity"],
        g_bme688_bsec_data["raw_gas"],
        g_bme688_bsec_data["stabilization_status"],
        g_bme688_bsec_data["run_in_status"],
        g_bme688_bsec_data["temperature"],
        g_bme688_bsec_data["humidity"],
        g_bme688_bsec_data["gas_percentage"],
        g_bme688_bsec_data["gas_percentage_accuracy"]
        ))
        client.commit()
    except Exception as e:
        logging.error(e)

if __name__ == "__main__":
    schedule.every().hour.at(":15").do(write_to_db)
    schedule.every().hour.at(":30").do(write_to_db)
    schedule.every().hour.at(":45").do(write_to_db)
    schedule.every().hour.at(":00").do(write_to_db)

    logging.info("Starting BME688 setup")
    bme = bme688_setup()

    logging.info("Starting BME688 thread")
    bme688_t = threading.Thread(target=bme688_thread)
    bme688_t.start()

    logging.info("Starting database schedules")
    try:
        while True:
            schedule.run_pending()
            sleep(1)
    except KeyboardInterrupt:
        client.close()
        sys.exit(0)
