from dash import Dash, html, dcc, callback, Output, Input
from dash_bootstrap_templates import load_figure_template
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import pymysql
from sqlalchemy import create_engine
import sys

# Comment/uncomment to select dropdown items (excluding timestamp)
col_to_label = {
    "timestamp": "Time",
    "iaq": "Indoor Air Quality (0-500)",
#    "iaq_accuracy": "Indoor Air Quality Accuracy (0-3)",
    "static_iaq": "Static Indoor Air Quality (0-500)",
#    "static_iaq_accuracy": "Static Indoor Air Quality Accuraxy (0-3)",
    "co2_equivalent": "CO2 Equivalents (ppm)",
#    "co2_accuracy": "CO2 Accuracy (0-3)",
#    "breath_voc_equivalent": "breath-VOC Equivalents (ppm)",
#    "breath_voc_accuracy": "breath-VOC Accuracy (0-3)",
#    "raw_temperature": "Raw Temperature",
#    "raw_pressure": "Raw Pressure",
#    "raw_humidity": "Raw Relative Humidity",
#    "raw_gas": "Raw Gas resistance",
#    "stabilization_status": "Stabilization Time Status",
#    "run_in_status": "Run In Status",
    "temperature": "Ambient Temperature (°C)",
    "humidity": "Ambient Relative Humidity (%)",
#    "gas_percentage": "Gas (%)",
#    "gas_percentage_accuracy": "Gas (%) Accuracy (0-3)"
}

label_to_col = {v: k for k, v in col_to_label.items()}
select_cols = ",".join(col_to_label.keys())
default_dropdown_selection = col_to_label["static_iaq"]
engine = None

with open("password.txt", "r") as f:
    pwd = f.read();
    usr = "db_reader"
    db = "bme688_telemetry"
    engine = create_engine(f"mysql+pymysql://{usr}:{pwd.rstrip()}@localhost/{db}", echo=False, pool_pre_ping=True)

SLATE = "assets/slate/bootstrap.min.css"
app = Dash(external_stylesheets=[SLATE])
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

load_figure_template(["darkly"])

app.layout = dbc.Container([
    html.H1(children="BME688", style={"textAlign":"center"}),
    dcc.Dropdown(id="dropdown-selection",
        options=[v for v in col_to_label.values() if v != col_to_label["timestamp"]],
        value=default_dropdown_selection,
        clearable=False),
    dcc.Graph(id="time-series-chart")
    ],
    className="dbc"
)

@app.callback(
    Output("time-series-chart", "figure"),
    Input("dropdown-selection", "value")
)
def update_graph(value):
    query = f"SELECT {select_cols} FROM time_series;"
    df = pd.read_sql(query, con=engine)
    val = label_to_col[value]
    fig = px.line(data_frame=df, x="timestamp", y=val, labels=col_to_label, template="plotly_dark")
    fig.update_yaxes(range=[0, 1.2 * df[val].max()])
    return fig

if __name__ == "__main__":
    app_host = "0.0.0.0"
    app_port = 8050
    if sys.argv.count("-debug") == 1:
        app.run(debug=True, host=app_host, port=app_port)
    else:
        from waitress import serve
        serve(app.server, host=app_host, port=app_port)
