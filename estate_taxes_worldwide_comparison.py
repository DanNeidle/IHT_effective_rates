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
# also requires kaleido package

max_estate_size = 100    # x axis max - largest estate size we chart, as multiple of average earnings


def add_line_for_UK_estate_value(fig, position, max_height, annotation_text, colour):
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
    return fig




estate_resolution = 0.1  # the steps we go up

excel_file = "estate-taxes_worldwide_data.xlsx"

logo_jpg = Image.open("logo_full_white_on_blue.jpg")

all_countries = []
country_max_effective_rate = []
country_estate_tax_of_GDP = []
country_max_statutory_rate = []

# create plotly graph object
# layout settings

logo_layout = [dict(
        source=logo_jpg,
        xref="paper", yref="paper",
        x=1, y=1.03,
        sizex=0.1, sizey=0.1,
        xanchor="right", yanchor="bottom"
    )]

layout = go.Layout(
    images=logo_layout,
    title="Estate value (as multiple of average earnings) vs theoretical effective IHT/estate tax rate<br>for children inheriting from two parents",
    xaxis=dict(
        title="Estate value (multiple of average earnings)",
        zeroline=True,
        range=[0, max_estate_size * 1.05],
        dtick=10
    ),
    yaxis=dict(
        title="Effective rate",
        tickformat=',.0%',  # so we get nice percentages,
        zeroline=True,
        range=[0, 0.40]
    ) )

fig = go.Figure(layout=layout)



print(f"Opening {excel_file}")
xl = pd.ExcelFile(excel_file)
print("")
print(f"Opened spreadsheet. Sheets: {xl.sheet_names}")

print("")
print("Data for export:")
print("-------------------------------")

df = xl.parse("IHT bands - children")

do_header = True

for country_row in range (0,len(df)):
    country_name = df.iat[country_row, 0]
    export_headings = " , "
    export_row = f"{country_name}, "

    x_data = []  # income multiple
    y_data = []  # effective rate

#   first load bands into a list of dicts
    band = 0
    bands = []
    while not pd.isna(df.iat[country_row, band * 2 + 5]):   # this keeps going til we hit a NaN
        threshold =  df.iat[country_row, band * 2 + 5]   # this is % of average earnings
        rate = df.iat[country_row, band * 2 + 6]
        bands.append({"threshold": threshold, "rate": rate})
        band += 1

    # add a dummy band higher than all estate values - makes algorithm for applying bands cleaner/easier
    bands.append({"threshold": 10000, "rate": df.iat[country_row, (band-1) * 2 + 6]})

    # print(f"bands: {bands}")

    # loop estate values 0 to 50 x average salary, in 0.1 increments
    for estate_value in [estate_value * estate_resolution for estate_value in range(0, int(max_estate_size / estate_resolution) + 1)]:

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
        #print(f"estate value: {round(estate_value, 1)} - effective tax rate {100*ETR}% (residence nil band is {resi_nil_rate_band})")
        x_data.append(round(estate_value,2))
        export_headings += f"{estate_value}, "

        y_data.append(ETR)
        export_row += f"{ETR}, "

    # let's keep countries with no IHT off the data - but include the US (as otherwise its high exemption will artifically exclude it)
    if bands[x]["rate"] == 0 and country_name != "United States":
        # print ("this country has no estate tax at this level - so nothing to plot! (and US will be in this category unless max_estate_size is large)")
        continue

    if do_header:
        print(export_headings)
        do_header = False

    print(export_row)

    # add label to last data item showing country (bit hacky; must be better way)
    labels = [""] * (int(max_estate_size / estate_resolution) - 1)
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

    # while we're at it, collate data for second chart
    all_countries.append(country_name)
    country_estate_tax_of_GDP.append(df.iat[country_row, 1])
    country_max_effective_rate.append(ETR)
    country_max_statutory_rate.append(bands[x]["rate"])

    # now loop to next country
print("-------------------------------")

uk_average_wage = 36987
fig = add_line_for_UK_estate_value(fig, 335000 / uk_average_wage, 0.40, "£335k (the UK average)<br>UK estate value", "Grey")
fig = add_line_for_UK_estate_value(fig, 1000000 / uk_average_wage, 0.40, "£1m<br>UK estate value", "Grey")
fig = add_line_for_UK_estate_value(fig, 2700000 / uk_average_wage, 0.40, "£2.7m<br>UK estate value", "Grey")
    
fig.add_annotation(
    dict(
        x=10,
        y=0.35,
        text="<b>No IHT/estate tax:</b><br>Hungary, Lithuania,<br>Portugal (for children), Poland,<br>Slovenia, Sweden, Switzerland",
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
    
fig.show()

print ("All done!")
exit()

# second chart - effective rate vs IHT as % of GDP
layout = go.Layout(
    images=logo_layout,
    title=f"Effective IHT/estate tax rate on estates {max_estate_size}x average earnings, vs tax collected as % of GDP",
    xaxis=dict(
        title="Effective IHT/estate tax rate",
        tickformat=',.0%'  # so we get nice percentages
    ),
    yaxis=dict(
        title="IHT/estate tax collected as % of GDP",
        tickformat='.2%'  # so we get nice percentages
    ))

fig2 = go.Figure(layout=layout)

fig2.add_trace(go.Scatter(
    x=country_max_effective_rate,
    y=country_estate_tax_of_GDP,
    mode="markers+text",  # no markers
    name="markers and Text",
    text=all_countries,
    textposition="top center",
    showlegend=False))

slope, intercept, r_value, p_value, std_err = stats.linregress(country_max_effective_rate, country_estate_tax_of_GDP)
best_fit_y = []

print(f"Slope {slope}, intercept {intercept}, r value{r_value}")

# create data for trendline
for x in country_max_effective_rate:
    best_fit_y.append(intercept + x * slope)

# plot trendline
fig2.add_trace(go.Scatter(
    x=country_max_effective_rate,
    y=best_fit_y,
    mode="lines",
    name="lines",
    showlegend=False))

fig2.show()
fig2.write_image(f"OECD_IHT_vs_GDP_{max_estate_size}x.svg")



# third chart - maximum rate vs IHT as % of GDP
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

fig3 = go.Figure(layout=layout)

fig3.add_trace(go.Scatter(
    x=country_max_statutory_rate,
    y=country_estate_tax_of_GDP,
    mode="markers+text",  # no markers
    name="markers and Text",
    text=all_countries,
    textposition="top center",
    showlegend=False))

fig3.add_layout_image(
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
fig3.add_trace(go.Scatter(
    x=country_max_statutory_rate,
    y=best_fit_y,
    mode="lines",
    name="lines",
    showlegend=False))

# now plot it:
fig3.show()

print("")
print("Data for export:")
print(all_countries)
print("")
print(country_max_statutory_rate)
print("")
print(country_estate_tax_of_GDP)
print ("------------")

print("All done!")