# inheritance tax, gift taxes and estate taxes worldwide
# theoretical effective rates for different estate values

# (c) Dan Neidle of Tax Policy Associates Ltd
# licensed under the GNU General Public License, version 2

# this plots two charts
# first, the effective rate of estate/inheritance/gift tax on estates worth different multiples of average income
# second, the max effective rate found from the above, vs % of GDP collected in tax

# IHT rate and threshold data, and median income data, all from the OECD
# all on basis that estate is being passed by a married couple to their children
# (some countries have different rates for passing to third parties)
# this therefore takes into account any previous spousal exemption

# the OECD data doesn't include the effect of the UK residence nil rate band - I have added it
# undoubtedly there are other special rules/exemptions in other jurisdictions not included in the data

import plotly.graph_objects as go
import pandas as pd
from scipy import stats
from PIL import Image
import csv

MAX_ESTATE_SIZE = 100    # x axis max - largest estate size we chart, as multiple of average earnings
ESTATE_RESOLUTION = 0.1  # the steps we go up
UK_AVERAGE_WAGE = 36987
Y_AXIS_HEIGHT = 0.40

LINES_TO_ADD_TO_CHART = {335000: "£335k (the UK average)<br>UK estate value",
                        1000000: "£1m<br>UK estate value",
                        2700000: "£2.7m<br>UK estate value"}

EXCEL_FILE = "estate-taxes_worldwide_data.xlsx"
EXCEL_TAB = "IHT bands - children"
LOGO_JPG_FILE = Image.open("logo_full_white_on_blue.jpg")
FORCE_PLOT_COUNTRIES = ["United States"]   # we will plot these, even if there is zero ETR


def dict_to_csv(data_dict, filename='estate_taxes_worldwide_comparison.csv'):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write headers
        writer.writerow(data_dict.keys())
        
        # Write data rows
        for row in zip(*data_dict.values()):
            writer.writerow(row)
            

def initialise_export_table():
    table = {}
    table["Estate value"] = []
    for estate_value in [estate_value * ESTATE_RESOLUTION for estate_value in range(0, int(MAX_ESTATE_SIZE / ESTATE_RESOLUTION) + 1)]:
        table["Estate value"].append(estate_value)
    return table

def create_layout_for_plot(logo_layout):

    return go.Layout(
        images=logo_layout,
        title="Estate value (as multiple of average earnings) vs theoretical effective IHT/estate tax rate<br>for children inheriting from two parents",
        xaxis=dict(
            title="Estate value (multiple of average earnings)",
            zeroline=True,
            range=[0, MAX_ESTATE_SIZE * 1.05],
            dtick=10
        ),
        yaxis=dict(
            title="Effective rate",
            tickformat=',.0%',  # so we get nice percentages,
            zeroline=True,
            range=[0, Y_AXIS_HEIGHT]
        ) )

def add_line_for_UK_estate_value(position, max_height, annotation_text, colour):
    fig.add_shape(
        dict(type="line", x0=position, x1=position, y0=0, y1=max_height * 1.1,
            line=dict(color=colour, width=3))
    )

    fig.add_annotation(
        dict(
            x=position - 0.1,
            y=max_height,
            text=annotation_text,
            showarrow=False,
            font=dict(
                size=12,
                color="black"
            ),
            align="right",
            xanchor="right",
            yanchor="top"
        )
    )
    
    
def add_annotations_to_chart():
    for amount, note in LINES_TO_ADD_TO_CHART.items():
        add_line_for_UK_estate_value(amount / UK_AVERAGE_WAGE, Y_AXIS_HEIGHT, note, "Grey")
    
    add_note_about_zero_iht_countres("<b>No IHT/estate tax:</b><br>Hungary, Lithuania,<br>Portugal (for children), Poland,<br>Slovenia, Sweden, Switzerland")
        
    
def add_note_about_zero_iht_countres(note_text):
    fig.add_annotation(
        dict(
            x=10,
            y=0.35,
            text=note_text,
            showarrow=False,
            font=dict(
                size=14,
                color="black"
            ),
            align="left",
            xanchor="left",
            yanchor="top"
        )
    )


def add_logo_layout():
    return [dict(
        source=LOGO_JPG_FILE,
        xref="paper", yref="paper",
        x=1, y=1.03,
        sizex=0.1, sizey=0.1,
        xanchor="right", yanchor="bottom"
    )]


def create_list_of_iht_bands(row_data):
#   first load bands into a list of dicts
    band = 0
    iht_bands = []
    while not pd.isna(df.iat[row_data, band * 2 + 5]):   # this keeps going til we hit a NaN
        threshold =  df.iat[row_data, band * 2 + 5]   # this is % of average earnings
        rate = df.iat[row_data, band * 2 + 6]
        iht_bands.append({"threshold": threshold, "rate": rate})
        band += 1

    # add a dummy band higher than all estate values - makes algorithm for applying bands cleaner/easier
    iht_bands.append({"threshold": 10000, "rate": df.iat[row_data, (band-1) * 2 + 6]})
    return iht_bands


def calculate_ETFs_for_country(country_name, bands, country_row):
    x_data = []  # income multiple
    y_data = []  # effective rate

    # loop estate values 0 to 50 x average salary, in 0.1 increments
    all_export_data[country_name] = []
    for estate_value in [estate_value * ESTATE_RESOLUTION for estate_value in range(0, int(MAX_ESTATE_SIZE / ESTATE_RESOLUTION) + 1)]:

        if estate_value == 0:
            # can't calculate ETR for zero value estates
            continue

        total_tax = 0

        if pd.isna(df.iat[country_row, 2]):
            # no nil rate residence band, i.e. not the UK!
            resi_nil_rate_band = 0
        else:
            resi_nil_rate_band = df.iat[country_row, 2]
            resi_taper_threshold = df.iat[country_row, 3]
            resi_taper_fraction = df.iat[country_row, 4]
            # print(f"This country has a residence nil rate band of {resi_nil_rate_band}, tapering after {resi_taper_threshold} at {resi_taper_fraction}")
            if estate_value > resi_taper_threshold:
                resi_nil_rate_band = max(0, resi_nil_rate_band - resi_taper_fraction * (estate_value - resi_taper_threshold))

        # take account of resi nil rate band, if any
        modified_estate_value = estate_value - resi_nil_rate_band

        for x in range(len(bands)):

            # if we hit the next threshold then apply tax to whole band
            if modified_estate_value >= bands[x+1]["threshold"]:
                total_tax += bands[x]["rate"] * (bands[x+1]["threshold"] - bands[x]["threshold"])  # we reach the next threshold!

            # otherwise apply tax to what's left in this band, then stop looping bands
            else:
                total_tax += bands[x]["rate"] * (modified_estate_value - bands[x]["threshold"])
                break

        ETR = total_tax/estate_value
        # print(f"estate value: {round(estate_value, 1)} - effective tax rate {100*ETR}% (residence nil band is {resi_nil_rate_band})")
        x_data.append(round(estate_value,2))

        y_data.append(ETR)
        all_export_data[country_name].append(ETR)
        
    return x_data, y_data, bands[-1]["rate"]


def plot_country_data(country_name, x_data, y_data):
    # add label to last data item showing country (bit hacky; must be better way)
    labels = [""] * (int(MAX_ESTATE_SIZE / ESTATE_RESOLUTION) - 1)
    labels.append(country_name)

    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode="lines+text",    # no markers
        name="Lines and Text",
        text=labels,
        textposition="top center",
        showlegend=False
    ))

if __name__ == "__main__":

    all_countries = []
    country_estate_tax_of_GDP = []
    country_max_statutory_rate = []

    logo_layout = add_logo_layout()
    fig = go.Figure(layout=create_layout_for_plot(logo_layout))

    xl = pd.ExcelFile(EXCEL_FILE)
    df = xl.parse(EXCEL_TAB)

    all_export_data = initialise_export_table()


    for country_row in range (0,len(df)):
        country_name = df.iat[country_row, 0]
        
        bands = create_list_of_iht_bands(country_row)
        x_data, y_data, max_rate = calculate_ETFs_for_country(country_name, bands, country_row)

        # Only plot for countries where there is IHT (the US is a special case)
        if max_rate > 0 or country_name in FORCE_PLOT_COUNTRIES:
            plot_country_data(country_name, x_data, y_data)

            # while we're at it, collate data for second chart
            all_countries.append(country_name)
            country_estate_tax_of_GDP.append(df.iat[country_row, 1])
            country_max_statutory_rate.append(max_rate)
        
    add_annotations_to_chart()
    
    fig.show()

    print ("All done!")
    dict_to_csv(all_export_data)

    # second chart - maximum rate vs IHT as % of GDP
    layout = go.Layout(
        images=logo_layout,
        title=f"Maximum statutory IHT/estate tax rate (children inheriting), vs tax collected as % of GDP",
        xaxis=dict(
            title="Maximum statutory IHT/estate tax rate",
            tickformat=',.0%'  # so we get nice percentages
        ),
        yaxis=dict(
            title="IHT/estate tax collected as % of GDP",
            tickformat='.2%'  # so we get nice percentages
        ))

    fig2 = go.Figure(layout=layout)

    fig2.add_trace(go.Scatter(
        x=country_max_statutory_rate,
        y=country_estate_tax_of_GDP,
        mode="markers+text",  # no markers
        name="markers and Text",
        text=all_countries,
        textposition="top center",
        showlegend=False))

    fig2.add_layout_image(
        dict(
            source="www.taxpolicy.org.uk/wp-content/uploads/2022/04/Asset-1@2x-8.png",
            xref="paper", yref="paper",
            x=0.1, y=0.01,
            sizex=0.2, sizey=0.2,
            xanchor="right", yanchor="bottom"
        )
    )


    slope, intercept, r_value, p_value, std_err = stats.linregress(country_max_statutory_rate, country_estate_tax_of_GDP)
    best_fit_y = []

    print(f"Slope {slope}, intercept {intercept}, r value{r_value}")

    # create data for trendline
    for x in country_max_statutory_rate:
        best_fit_y.append(intercept + x * slope)

    # plot trendline
    fig2.add_trace(go.Scatter(
        x=country_max_statutory_rate,
        y=best_fit_y,
        mode="lines",
        name="lines",
        showlegend=False))

    # now plot it:
    fig2.show()

    print("All done!")