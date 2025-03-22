import dash
from dash import dcc, html, dash_table
import plotly.express as px
import pandas as pd
from datetime import datetime

# Load and process data
df = pd.read_csv('dataset/Vending_Machine_Sales_Data_Singapore.csv')
df['Date'] = pd.to_datetime(df['Date'])

#color palette
colors = {
    'primary': '#43A047',  
    'secondary': '#43A047',
    'accent': '#FFB300', 
    'light_bg': '#ffffff',
    'text': '#333333', 
    'table_header': '#00941c', 
    'border': '#b7e6b9',  
    'hover': '#a4f9c1' 
}

# Define a custom colorscale for charts
category_colors = px.colors.qualitative.Bold

# Calculate total sales and other metrics (same as original)
total_sales = df.groupby(['Machine_ID', 'Location_Type', 'Product_ID', 'Product_Name'])['Units_Sold'].sum().reset_index()
total_sales.rename(columns={'Units_Sold': 'Total_Units_Sold'}, inplace=True)

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

# Custom CSS for better styling
external_stylesheets = [
    {
        'href': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
        'rel': 'stylesheet'
    },
    {
        'href': 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap',
        'rel': 'stylesheet'
    }
]

# Initialize Dash app with external stylesheets
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Custom styles
card_style = {
    'backgroundColor': colors['light_bg'],
    'borderRadius': '8px',
    'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
    'padding': '20px',
    'margin': '15px 0',
    'border': f'1px solid {colors["border"]}'
}

header_style = {
    'color': colors['primary'],
    'fontFamily': 'Roboto, sans-serif',
    'fontWeight': 'bold',
    'textAlign': 'center',
    'marginBottom': '20px',
    'paddingBottom': '10px',
    'borderBottom': f'2px solid {colors["border"]}'
}

dropdown_style = {
    'width': '100%',
    'borderRadius': '4px',
    'border': f'2px solid {colors["border"]}',
    'backgroundColor': 'white',
    'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)',
    'fontFamily': 'Roboto, sans-serif'
}

graph_style = {
    'border': f'1px solid {colors["border"]}',
    'borderRadius': '8px',
    'margin': '15px 0',
    'padding': '10px',
    'backgroundColor': 'white',
    'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
}

# Define the layout with improved styling
app.layout = html.Div([
    # Header
    html.Div([
        html.I(className="fas fa-chart-line", style={'fontSize': '28px', 'marginRight': '10px', 'color': colors['primary']}),
        html.H1("Vending Machine Stock Level Dashboard", style={'display': 'inline', 'color': colors['primary']})
    ], style={'textAlign': 'center', 'marginBottom': '20px', 'paddingBottom': '10px', 'borderBottom': f'2px solid {colors["border"]}'}),
    
    # Dropdown selection card
    html.Div([
        html.Label([
            html.I(className="fas fa-filter", style={'marginRight': '8px', 'color': colors['primary']}),
            "Select Vending Machine:"
        ], style={'color': colors['primary'], 'fontWeight': 'bold', 'marginBottom': '10px', 'fontSize': '16px'}),
        dcc.Dropdown(
            id='machine-dropdown',
            options=[{'label': 'ALL MACHINES', 'value': 'ALL'}] + [{'label': machine, 'value': machine} for machine in df['Location_Type'].unique()],
            value='ALL',
            style=dropdown_style
        )
    ], style={**card_style, 'width': '50%', 'margin': '20px auto'}),

    # Overall Statistics Section (visible when "ALL MACHINES" is selected)
    html.Div([
        html.H2([
            html.I(className="fas fa-chart-pie", style={'marginRight': '10px'}),
            "Overall Statistics"
        ], style=header_style),
        
        # Line chart
        html.Div([
            dcc.Graph(id='overall-units-sold-line')
        ], style=graph_style),
        
        # Area chart
        html.Div([
            dcc.Graph(id='overall-units-sold-area')
        ], style=graph_style),
        
        # Pie chart
        html.Div([
            dcc.Graph(id='overall-sales-pie')
        ], style=graph_style)
    ], id='overall-stats', style={**card_style, 'display': 'block'}),  # Initially visible

    # Selected Machine Statistics Section (visible when a specific machine is selected)
    html.Div([
        html.H2([
            html.I(className="fas fa-store", style={'marginRight': '10px'}),
            "Selected Machine Statistics"
        ], style=header_style),
        
        # Line chart
        html.Div([
            dcc.Graph(id='selected-units-sold-line')
        ], style=graph_style),
        
        # Bar chart
        html.Div([
            dcc.Graph(id='selected-recommended-stock-bar')
        ], style=graph_style),
        
        # Data table
        html.Div([
            html.H3("Stock Levels and Order Quantities", style={'color': colors['primary'], 'textAlign': 'center', 'marginBottom': '10px'}),
            dash_table.DataTable(
                id='selected-machine-table',
                columns=[{"name": i, "id": i} for i in final_order_df.columns],
                style_header={
                    'backgroundColor': colors['table_header'],
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'borderBottom': '2px solid white',
                    'borderRadius': '4px 4px 0 0'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px 15px',
                    'backgroundColor': 'white',
                    'color': colors['text'],
                    'fontFamily': 'Roboto, sans-serif',
                    'fontSize': '14px',
                    'border': f'1px solid {colors["border"]}'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': colors['light_bg']
                    },
                    {
                        'if': {'column_id': 'Order_Quantity', 'filter_query': '{Order_Quantity} > 0'},
                        'backgroundColor': '#FFEBEE',
                        'color': '#D32F2F',
                        'fontWeight': 'bold'
                    }
                ],
                style_table={
                    'border': f'1px solid {colors["border"]}',
                    'borderRadius': '4px',
                    'overflow': 'hidden',
                    'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
                },
                page_size=10,
                sort_action='native',
                filter_action='native',
                style_as_list_view=True,
            )
        ], style={'marginTop': '20px'})
    ], id='selected-stats', style={**card_style, 'display': 'none'})  # Initially hidden
], style={'backgroundColor': colors['light_bg'], 'padding': '20px', 'fontFamily': 'Roboto, sans-serif', 'maxWidth': '1200px', 'margin': '0 auto'})

# Callback to toggle visibility between overall and selected stats
@app.callback(
    [dash.dependencies.Output('overall-stats', 'style'),
     dash.dependencies.Output('selected-stats', 'style')],
    [dash.dependencies.Input('machine-dropdown', 'value')]
)
def toggle_sections(selected_machine):
    if selected_machine == 'ALL':
        return {**card_style, 'display': 'block'}, {**card_style, 'display': 'none'}
    else:
        return {**card_style, 'display': 'none'}, {**card_style, 'display': 'block'}

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
    fig_line.update_traces(
        line=dict(color=colors['primary'], width=3),
        mode='lines+markers',
        marker=dict(size=6, color=colors['primary'])
    )
    fig_line.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        title_font=dict(family="Roboto, sans-serif", color=colors['primary'], size=18),
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode='x unified',
        xaxis=dict(
            showgrid=True,
            gridcolor='#EEEEEE',
            title_font=dict(family="Roboto, sans-serif", color=colors['text']),
            tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#EEEEEE',
            title_font=dict(family="Roboto, sans-serif", color=colors['text']),
            tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
        )
    )

    # Units sold by machine over time
    machine_units = df.groupby(['Date', 'Machine_ID'])['Units_Sold'].sum().reset_index()
    fig_area = px.area(
        machine_units, 
        x='Date', 
        y='Units_Sold', 
        color='Machine_ID', 
        title='Units Sold by Machine Over Time',
        color_discrete_sequence=category_colors
    )
    fig_area.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        title_font=dict(family="Roboto, sans-serif", color=colors['primary'], size=18),
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode='x unified',
        legend=dict(
            title_font=dict(family="Roboto, sans-serif", color=colors['text']),
            font=dict(family="Roboto, sans-serif", color=colors['text'])
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor='#EEEEEE',
            title_font=dict(family="Roboto, sans-serif", color=colors['text']),
            tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#EEEEEE',
            title_font=dict(family="Roboto, sans-serif", color=colors['text']),
            tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
        )
    )

    # Sales distribution by category
    product_sales = df.groupby('Product_Name')['Units_Sold'].sum().reset_index()
    fig_pie = px.pie(
        product_sales, 
        values='Units_Sold', 
        names='Product_Name', 
        title='Sales Distribution by Product',
        color_discrete_sequence=category_colors,
        hole=0.4  
    )
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent+label',
        marker=dict(line=dict(color='white', width=2)),
        pull=[0.05 if i == product_sales['Units_Sold'].idxmax() else 0 for i in range(len(product_sales))]  # Pull out the largest segment
    )
    fig_pie.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        title_font=dict(family="Roboto, sans-serif", color=colors['primary'], size=18),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5,
            font=dict(family="Roboto, sans-serif", color=colors['text'])
        ),
        annotations=[dict(
            text='Total Units:<br>' + f"{product_sales['Units_Sold'].sum():,}",
            showarrow=False,
            font=dict(size=14, family="Roboto, sans-serif", color=colors['primary']),
            x=0.5,
            y=0.5
        )]
    )

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
        # Return empty figures and table when "ALL" is selected
        empty_fig = {
            'data': [],
            'layout': {
                'title': {'text': 'Please select a specific machine', 'font': {'family': 'Roboto, sans-serif', 'color': colors['primary']}},
                'paper_bgcolor': 'white',
                'plot_bgcolor': 'white'
            }
        }
        return empty_fig, empty_fig, []
    else:
        # Filter data for the selected machine
        machine_df = df[df['Location_Type'] == selected_machine]
        machine_units = machine_df.groupby('Date')['Units_Sold'].sum().reset_index()
        
        # Create the line chart with enhanced styling
        fig_line = px.line(
            machine_units, 
            x='Date', 
            y='Units_Sold', 
            title=f'Units Sold Over Time - {selected_machine}'
        )
        fig_line.update_traces(
            line=dict(color=colors['primary'], width=3),
            mode='lines+markers',
            marker=dict(size=6, color=colors['primary'])
        )
        fig_line.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            title_font=dict(family="Roboto, sans-serif", color=colors['primary'], size=18),
            margin=dict(l=40, r=40, t=50, b=40),
            hovermode='x unified',
            xaxis=dict(
                showgrid=True,
                gridcolor='#EEEEEE',
                title_font=dict(family="Roboto, sans-serif", color=colors['text']),
                tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#EEEEEE',
                title_font=dict(family="Roboto, sans-serif", color=colors['text']),
                tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
            ),
            height=400
        )

        # Create the bar chart with enhanced styling
        machine_sales_data = sales_data[sales_data['Location_Type'] == selected_machine]
        
        # Add the current stock level to the display
        stock_data = final_order_df[final_order_df['Location_Type'] == selected_machine]
        merged_data = machine_sales_data.merge(
            stock_data[['Product_Name', 'Current_Stock_Level']], 
            on='Product_Name', 
            how='left'
        )
        
        # Prepare data for grouped bar chart
        bar_data = []
        for _, row in merged_data.iterrows():
            bar_data.append({
                'Product_Name': row['Product_Name'],
                'Value': row['Current_Stock_Level'],
                'Type': 'Current Stock'
            })
            bar_data.append({
                'Product_Name': row['Product_Name'],
                'Value': row['Recommended_Stock_Level'],
                'Type': 'Recommended Stock'
            })
            
        bar_df = pd.DataFrame(bar_data)
        
        # Create grouped bar chart
        fig_bar = px.bar(
            bar_df, 
            x='Product_Name', 
            y='Value', 
            color='Type', 
            barmode='group',
            title=f'Stock Levels - {selected_machine}',
            color_discrete_map={
                'Current Stock': colors['accent'],
                'Recommended Stock': colors['secondary']
            }
        )
        fig_bar.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            title_font=dict(family="Roboto, sans-serif", color=colors['primary'], size=18),
            margin=dict(l=40, r=40, t=50, b=100),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            xaxis=dict(
                title='Product',
                tickangle=45,
                title_font=dict(family="Roboto, sans-serif", color=colors['text']),
                tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
            ),
            yaxis=dict(
                title='Units',
                title_font=dict(family="Roboto, sans-serif", color=colors['text']),
                tickfont=dict(family="Roboto, sans-serif", color=colors['text'])
            ),
            height=450
        )

        # Get table data
        machine_order_df = final_order_df[final_order_df['Location_Type'] == selected_machine]
        table_data = machine_order_df.to_dict('records')

        return fig_line, fig_bar, table_data

# Run the app
if __name__ == '__main__':
    app.run(debug=True)