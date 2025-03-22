import dash
from dash import dcc, html, dash_table
import plotly.express as px
import pandas as pd
from datetime import datetime

df = pd.read_csv('dataset/Vending_Machine_Sales_Data_Singapore.csv')
df['Date'] = pd.to_datetime(df['Date'])
# print(df.head())

total_sales = df.groupby(['Machine_ID', 'Location_Type', 'Product_ID', 'Product_Name'])['Units_Sold'].sum().reset_index()
total_sales.rename(columns={'Units_Sold': 'Total_Units_Sold'}, inplace=True)
# print(total_sales)

# Count unique active days
active_days = df.groupby(['Machine_ID', 'Location_Type', 'Product_ID'])['Date'].nunique().reset_index()
active_days.rename(columns={'Date': 'Active_Days'}, inplace=True)

# Merge total sales and active days
sales_data = total_sales.merge(active_days, on=['Machine_ID', 'Location_Type', 'Product_ID'])

# Calculate average daily sales
sales_data['Avg_Daily_Sales'] = (sales_data['Total_Units_Sold'] / sales_data['Active_Days']).round(2)

# Merge lead time
lead_time = df.groupby(['Machine_ID', 'Location_Type', 'Product_ID'])['Lead_Time_Days'].mean().reset_index()
sales_data = sales_data.merge(lead_time, on=['Machine_ID', 'Location_Type', 'Product_ID'])

# Calculate restock frequency and safety stock
sales_data['Restock_Frequency_Days'] = (12 / sales_data['Avg_Daily_Sales']).round().clip(lower=2, upper=10)
sales_data['Safety_Stock'] = (sales_data['Avg_Daily_Sales'] * 0.2).round()

# Calculate recommended stock level
sales_data['Recommended_Stock_Level'] = (
    sales_data['Avg_Daily_Sales'] * (sales_data['Restock_Frequency_Days'] + sales_data['Lead_Time_Days']) + 
    sales_data['Safety_Stock']
).round()

# Add category information
category_lookup = df[['Product_ID', 'Category']].drop_duplicates()
sales_data = sales_data.merge(category_lookup, on='Product_ID', how='left')

# Get latest stock levels
latest_stock = df.sort_values('Date').groupby(['Machine_ID', 'Product_ID'])['Current_Stock_Level'].last().reset_index()
latest_stock['Current_Stock_Level'] = latest_stock['Current_Stock_Level'].round().astype(int)

# Merge with sales data and calculate order quantity
final_order_df = sales_data.merge(latest_stock, on=['Machine_ID', 'Product_ID'], how='left')
final_order_df['Order_Quantity'] = (final_order_df['Recommended_Stock_Level'] - final_order_df['Current_Stock_Level']).clip(lower=0).round().astype(int)
final_order_df = final_order_df[['Machine_ID', 'Location_Type', 'Product_Name', 'Category', 'Current_Stock_Level', 'Recommended_Stock_Level', 'Order_Quantity']]

# Initialize Dash app
app = dash.Dash(__name__)

# Define the layout
app.layout = html.Div([
    html.H1("Vending Machine Stock Level Dashboard", style={'color': '#006400', 'textAlign': 'center', 'marginBottom': '20px'}),
    html.Div([
        html.Label("Select Vending Machine:", style={'color': '#006400', 'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='machine-dropdown',
            options=[{'label': 'ALL MACHINES', 'value': 'ALL'}] + [{'label': machine, 'value': machine} for machine in df['Machine_ID'].unique()],
            value='ALL',
            style={'width': '100%'}
        )
    ], style={'width': '50%', 'margin': 'auto', 'padding': '10px'}),

    # Overall Statistics Section (visible when "ALL MACHINES" is selected)
    html.Div([
        html.H2("Overall Statistics", style={'color': '#006400', 'textAlign': 'center', 'marginTop': '20px'}),
        dcc.Graph(id='overall-units-sold-line', style={'border': '2px solid #90EE90', 'margin': '10px'}),
        dcc.Graph(id='overall-units-sold-area', style={'border': '2px solid #90EE90', 'margin': '10px'}),
        dcc.Graph(id='overall-sales-pie', style={'border': '2px solid #90EE90', 'margin': '10px'})
    ], id='overall-stats', style={'display': 'block'}),  # Initially visible

    # Selected Machine Statistics Section (visible when a specific machine is selected)
    html.Div([
        html.H2("Selected Machine Statistics", style={'color': '#006400', 'textAlign': 'center', 'marginTop': '20px'}),
        dcc.Graph(id='selected-units-sold-line', style={'border': '2px solid #90EE90', 'margin': '10px'}),
        dcc.Graph(id='selected-recommended-stock-bar', style={'border': '2px solid #90EE90', 'margin': '10px'}),
        dash_table.DataTable(
            id='selected-machine-table',
            columns=[{"name": i, "id": i} for i in final_order_df.columns],
            style_header={'backgroundColor': '#006400', 'color': 'white', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'backgroundColor': 'white', 'color': 'black'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F5F5F5'}],
            style_table={'border': '2px solid #90EE90', 'margin': '10px'}
        )
    ], id='selected-stats', style={'display': 'none'})  # Initially hidden
], style={'backgroundColor': 'white', 'padding': '20px'})

# Callback to toggle visibility between overall and selected stats
@app.callback(
    [dash.dependencies.Output('overall-stats', 'style'),
     dash.dependencies.Output('selected-stats', 'style')],
    [dash.dependencies.Input('machine-dropdown', 'value')]
)
def toggle_sections(selected_machine):
    if selected_machine == 'ALL':
        return {'display': 'block'}, {'display': 'none'}  # Show overall stats, hide selected stats
    else:
        return {'display': 'none'}, {'display': 'block'}  # Hide overall stats, show selected stats

# Callback for overall graphs (updates when "ALL MACHINES" is selected)
@app.callback(
    [dash.dependencies.Output('overall-units-sold-line', 'figure'),
     dash.dependencies.Output('overall-units-sold-area', 'figure'),
     dash.dependencies.Output('overall-sales-pie', 'figure')],
    [dash.dependencies.Input('machine-dropdown', 'value')]
)
def update_overall_graphs(selected_machine):
    # Total units sold over time
    overall_units = df.groupby('Date')['Units_Sold'].sum().reset_index()
    fig_line = px.line(overall_units, x='Date', y='Units_Sold', title='Total Units Sold Over Time')
    fig_line.update_traces(line_color='#006400')
    fig_line.update_layout(paper_bgcolor='white', plot_bgcolor='white', title_font_color='#006400')

    # Units sold by machine over time
    machine_units = df.groupby(['Date', 'Machine_ID'])['Units_Sold'].sum().reset_index()
    fig_area = px.area(machine_units, x='Date', y='Units_Sold', color='Machine_ID', title='Units Sold by Machine Over Time')
    fig_area.update_layout(paper_bgcolor='white', plot_bgcolor='white', title_font_color='#006400')

    # Sales distribution by category
    category_sales = df.groupby('Category')['Units_Sold'].sum().reset_index()
    fig_pie = px.pie(category_sales, values='Units_Sold', names='Category', title='Sales Distribution by Category')
    fig_pie.update_layout(paper_bgcolor='white', plot_bgcolor='white', title_font_color='#006400')

    return fig_line, fig_area, fig_pie

# Callback for selected machine graphs (updates when a specific machine is selected)
@app.callback(
    [dash.dependencies.Output('selected-units-sold-line', 'figure'),
     dash.dependencies.Output('selected-recommended-stock-bar', 'figure'),
     dash.dependencies.Output('selected-machine-table', 'data')],
    [dash.dependencies.Input('machine-dropdown', 'value')]
)
def update_selected_machine_graphs(selected_machine):
    if selected_machine == 'ALL':
        # Return empty figures and table when "ALL" is selected (though this section will be hidden)
        empty_fig = {
            'data': [],
            'layout': {
                'title': {'text': 'Please select a specific machine', 'font': {'color': '#006400'}},
                'paper_bgcolor': 'white',
                'plot_bgcolor': 'white'
            }
        }
        return empty_fig, empty_fig, []
    else:
        # Filter data for the selected machine
        machine_df = df[df['Machine_ID'] == selected_machine]
        machine_units = machine_df.groupby('Date')['Units_Sold'].sum().reset_index()
        
        # Create the line chart with modified layout
        fig_line = px.line(machine_units, x='Date', y='Units_Sold', title=f'Units Sold Over Time - {selected_machine}')
        fig_line.update_traces(line_color='#006400')
        fig_line.update_layout(
            paper_bgcolor='white', 
            plot_bgcolor='white', 
            title_font_color='#006400',
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50),
            height=500,
            width=None 
        )

        # Create the bar chart
        machine_sales_data = sales_data[sales_data['Machine_ID'] == selected_machine]
        fig_bar = px.bar(machine_sales_data, x='Product_Name', y='Recommended_Stock_Level', title=f'Recommended Stock Levels - {selected_machine}')
        fig_bar.update_traces(marker_color='#006400')
        fig_bar.update_layout(
            paper_bgcolor='white', 
            plot_bgcolor='white', 
            title_font_color='#006400', 
            xaxis={'tickangle': 45},
            autosize=True,  
            margin=dict(l=50, r=50, t=80, b=100),
            height=500  
        )

        machine_order_df = final_order_df[final_order_df['Machine_ID'] == selected_machine]
        table_data = machine_order_df.to_dict('records')

        return fig_line, fig_bar, table_data

# Run the app
if __name__ == '__main__':
    app.run(debug=True)