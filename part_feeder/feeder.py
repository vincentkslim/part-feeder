import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ClientsideFunction

from flask import request

import plotly
import plotly.graph_objs as go

import numpy as np

import json, math
from urllib.parse import parse_qs
from typing import Union, List

from . import engine
from . import explanations
from . import anim
from . import utils
from .db import get_db

displays = {}

# global dropdown selector codes
sq_anim = 'sq_anim'
pg_anim = 'pg_anim'
stop = 'stop'
load_key = 'load'

error_message = 'Error! Polygon vertices not correctly specified. Please go back to the previous page and try again.'


def init_feeder(server):
    """Create the plots using plotly and dash."""
    dash_app = dash.Dash(
        __name__,
        server=server,
        routes_pathname_prefix='/part-feeder/feeder/',
        update_title=None,
        title='Part Feeder',
        external_scripts=["https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML"],
        external_stylesheets=[dbc.themes.BOOTSTRAP]
    )

    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(
            id='page-content',
            style={'visibility': 'hidden'},
            children=[
                html.Div(
                    id='plots',
                ),  # this displays all the plots and explanations
                dcc.Interval(
                    id='data_update_interval',
                    interval=8_000,
                    disabled=False
                ),
                dcc.Interval(
                    id='anim_update_interval',
                    interval=50,
                    disabled=False
                ),
                dcc.Store(
                    id='anim_data',
                    data=[],
                    storage_type='memory'
                ),
                dcc.Store(
                    id='anim_holding_data',  # hold data here, wait for clientside callback to update it.
                    data=[],
                    storage_type='memory'
                ),
                dcc.Store(
                    id='prev_anim',
                    storage_type='memory',
                ),
                dcc.Store(                  # holds information like the plans, transfer functions, etc.
                    id='anim_state',
                    data={},
                    storage_type='memory'
                ),
                dcc.Store(                  # holds the angles of all the polygons the last time this was queried.
                    id='anim_angles',
                    data={'sqPolygonAngles': [], 'pgPolygonAngles': []},
                    storage_type='memory'
                ),
                dcc.Dropdown(  # dropdown selector to determine which animation to display.
                    id='anim_selector',
                    options=[
                        {'label': 'Squeeze Plan', 'value': sq_anim},
                        {'label': 'Push Grasp Plan', 'value': pg_anim},
                        {'label': 'Stop Animation', 'value': stop}
                    ],
                    searchable=False,
                    style={'display': 'block'},
                    clearable=False,
                    value=pg_anim
                ),
                dcc.Graph(  # animation figure
                    id='anim',
                    style={'height': '50vh', 'margin': 'auto', 'display': 'block'},
                    config={'displayModeBar': False, 'staticPlot': True}
                ),
                dcc.Markdown(
                    id='contact',
                    style={'text-align': 'center', 'padding-top': '20px', 'padding-bottom': '20px'},
                    children='''For questions, comments or other thoughts, contact us at: 
                    *vincentklim {at} berkeley.edu* or *goldberg {at} berkeley.edu*'''
                )
            ]
        ),
        html.Div(
            id='loading_div',
            children=[
                'Loading...', html.Br(),
                dbc.Progress(
                    id='loading_bar'
                ),
                html.Div(
                    id='loading_text',
                    children=[],
                    style={'margin': 'auto', 'width': '100%', 'padding': '10px',
                           'text-align': 'center', 'font-size': 'large',
                           'white-space': 'pre-wrap'}
                ),
                dcc.Interval(
                    id='loading_interval',
                    interval=1000,
                    disabled=False
                )
            ],
            style={'display': 'block', 'width': '50%', 'left': '25%', 'position': 'absolute', 'top': '25%'}
        )
    ]
    )

    init_callbacks(dash_app)

    return dash_app.server


def get_request_hash(search_str):
    return utils.get_hash(search_str, request.remote_addr, request.headers.get("User-Agent"))


def init_callbacks(app):
    @app.callback(
        Output('plots', 'children'),
        Output('anim_state', 'data'),
        Input('url', 'search'))
    def display_feeder(search: str):
        """
        This parses a list of vertices describing a polygon from the query string in the URL.
        """
        search_str = search
        if search and search[0] == '?':
            search = search[1:]
        if not search:
            return error_message
        points = parse_qs(search)

        if 'x' not in points or 'y' not in points or len(points['x']) != len(points['y']) or len(points['x']) < 3:
            return error_message

        assert 'x' in points
        assert 'y' in points
        assert len(points['x']) == len(points['y'])

        try:
            db, Part = get_db()
            dumps = json.dumps(points)
            exists = Part.query.filter_by(points=dumps).first()
            if not exists:
                db.session.add(Part(points=dumps))
                db.session.commit()
        except Exception as e:
            pass
            # just so that the wip database does not affect anything for now.

        x = list(map(int, points['x']))
        y = list(map(int, points['y']))

        points = np.hstack((np.array(x).reshape((-1, 1)), np.array(y).reshape((-1, 1))))
        points = engine.scale_and_center_polygon(points)

        return create_page(points, get_request_hash(search_str))

    app.clientside_callback(  # This clientside callback is a little bit of a hack but it works.
        """
        function(n, value, data, holding_data, prev) {
            if (value !== "stop" && value !== prev) {
                // clear out data
                data.length = 0;
            }
            for (var i=0; i<holding_data.length; i++) {
                data.push(holding_data.shift());
            }
            if (data.length > 1) {
                return data.shift(); //[data[0], data.slice(1)];
            } else if (data.length == 1) {
                return data[0]; //[data[0], data];
            }
        }
        """,
        Output('anim', 'figure'),
        Input('anim_update_interval', 'n_intervals'),
        Input('anim_selector', 'value'),
        State('anim_data', 'data'),
        State('anim_holding_data', 'data'),
        State('prev_anim', 'data')
    )

    app.clientside_callback(
        ClientsideFunction(
            namespace='clientside',
            function_name='updateAnim'
        ),
        Output('anim_holding_data', 'data'),
        Output('anim_angles', 'data'),
        Output('data_update_interval', 'disabled'),
        Output('anim_update_interval', 'disabled'),
        Output('prev_anim', 'data'),
        Input('data_update_interval', 'n_intervals'),
        Input('anim_selector', 'value'),
        State('anim_state', 'data'),
        State('anim_angles', 'data'),
        State('prev_anim', 'data')
    )

    @app.callback(
        Output('page-content', 'style'),
        Output('loading_div', 'style'),
        Output('loading_interval', 'disabled'),
        Input('plots', 'children'),
        State('url', 'search')
    )
    def show_anim(content, search_str):
        if content and content != error_message:
            del displays[get_request_hash(search_str)]
            return {'visibility': 'visible'}, {'display': 'none'}, True
        elif content == error_message:
            return {'display': 'none'}, {'display': 'none'}, True
        return {'visibility': 'hidden'}, {'display': 'block'}, False

    @app.callback(
        Output('loading_text', 'children'),
        Output('loading_bar', 'value'),
        Output('loading_bar', 'children'),
        Input('loading_interval', 'n_intervals'),
        State('url', 'search')
    )
    def pbar(_, search_str):
        search = get_request_hash(search_str)
        if search in displays:
            progress = len(displays[search][load_key]) / 18 * 100
            return displays[search][load_key], round(progress), f'{round(progress)}%'

        return [], 0, 0


def update_loading(hash_str, message):
    displays[hash_str][load_key].append(html.Code(children='{:<40s}'.format(message)))


def update_loading_done(hash_str):
    displays[hash_str][load_key][-1].children += 'done'
    displays[hash_str][load_key].append(html.Br())


def create_page(points, hash_str):
    s_domain = (0, 2 * np.pi)  # s_domain refers to all squeeze function related domains
    pg_domain = (0, 4 * np.pi)  # pg_domain refers to all push-grasp function related domains

    latex = request.user_agent.browser != 'firefox'  # mathjax latex rendering is broken on firefox

    displays[hash_str] = {load_key: []}

    ch = engine.convex_hull(points)
    antipodal_pairs = engine.antipodal_pairs(ch)

    # Diameter function
    update_loading(hash_str, 'Generating diameter function')
    piecewise_diameter = engine.make_diameter_function(ch)

    bounded_piecewise_diameter = engine.generate_bounded_piecewise_func(piecewise_diameter, period=np.pi)
    diameter_callable = engine.generate_bounded_callable(bounded_piecewise_diameter, period=np.pi)
    diameter_maxima, diameter_minima = engine.find_bounded_extrema(bounded_piecewise_diameter,
                                                                   period=np.pi, domain=s_domain)
    update_loading_done(hash_str)

    # Squeeze function
    update_loading(hash_str, 'Generating squeeze function')
    squeeze_func = engine.generate_transfer_from_extrema(diameter_minima, diameter_maxima)
    squeeze_callable = engine.generate_transfer_extrema_callable(squeeze_func, period=np.pi)
    update_loading_done(hash_str)

    # Radius function
    update_loading(hash_str, 'Generating radius function')
    piecewise_radius = engine.make_radius_function(ch)
    bounded_piecewise_radius = engine.generate_bounded_piecewise_func(piecewise_radius, period=2 * np.pi)
    radius_callable = engine.generate_bounded_callable(bounded_piecewise_radius, period=2 * np.pi)
    radius_maxima, radius_minima = engine.find_bounded_extrema(bounded_piecewise_radius,
                                                               period=2 * np.pi, domain=pg_domain)
    update_loading_done(hash_str)

    # Push function
    update_loading(hash_str, 'Generating push function')
    push_func = engine.generate_transfer_from_extrema(radius_minima, radius_maxima)
    push_callable = engine.generate_transfer_extrema_callable(push_func, period=2 * np.pi)
    update_loading_done(hash_str)

    # Push-grasp function
    update_loading(hash_str, 'Generating push-grasp function')
    extended_squeeze = engine.generate_transfer_from_extrema(
        *reversed(engine.find_bounded_extrema(bounded_piecewise_diameter, period=np.pi, domain=pg_domain, buffer=4))
    )
    push_grasp_func = engine.generate_bounded_push_grasp_function(push_func, extended_squeeze)
    push_grasp_callable = engine.generate_transfer_extrema_callable(push_grasp_func, period=2 * np.pi)
    update_loading_done(hash_str)

    # generate squeeze plan
    update_loading(hash_str, 'Generating squeeze plan')
    sq_intervals = engine.generate_intervals(squeeze_func, default_T=np.pi)
    sq_plan = engine.generate_plan(sq_intervals)
    update_loading_done(hash_str)

    # generate push-grasp plan
    update_loading(hash_str, 'Generating push-grasp plan')
    pg_intervals = engine.generate_intervals(push_grasp_func, default_T=2 * np.pi)
    pg_plan = engine.generate_plan(pg_intervals)
    update_loading_done(hash_str)

    # create display
    update_loading(hash_str, 'Generating animation simulator')
    # ported to javascript!
    update_loading_done(hash_str)

    # Create figures
    update_loading(hash_str, 'Generating plots')
    pad = 0.025      # normalized distance below/to the left of the axis to place the intervals
    ch_ap_graph = create_graph_from_figure(
        create_antipodal_pairs_figure(points, ch, antipodal_pairs), 'ch_ap_fig')
    dia_graph = create_graph_from_figure(
        create_function_figure(diameter_callable, diameter_minima, diameter_maxima, s_domain, latex), 'dia_fig')
    sq_graph = create_graph_from_figure(
        add_intervals_to_figure(create_transfer_figure(squeeze_callable, s_domain, latex), sq_intervals,
                                offset=s_domain[0]-pad*(s_domain[1]-s_domain[0])), 'sq_fig')

    rad_graph = create_graph_from_figure(
        create_function_figure(radius_callable, radius_minima, radius_maxima, pg_domain, latex), 'rad_fig')
    pu_graph = create_graph_from_figure(
        create_transfer_figure(push_callable, pg_domain, latex), 'pu_fig')

    pg_graph = create_graph_from_figure(
        add_intervals_to_figure(create_transfer_figure(push_grasp_callable, pg_domain, latex), pg_intervals,
                                offset=pg_domain[0]-pad*(pg_domain[1]-pg_domain[0]), increment=0.2), 'pg_fig')
    update_loading_done(hash_str)

    state = {
        'points': [dict(zip(('x', 'y',), p)) for p in points],
        'convexhull': [dict(zip(('x', 'y',), p)) for p in ch],
        'sqPlan': sq_plan,
        'pgPlan': pg_plan,
        'squeezeFunc': squeeze_func,
        'diameterFunc': bounded_piecewise_diameter,
        'radiusFunc': bounded_piecewise_radius,
        'pushFunc': push_func,
        'pushGraspFunc': push_grasp_func
    }

    return [explanations.ch_ap, ch_ap_graph,
            explanations.dia, dia_graph,
            explanations.sq, sq_graph,
            explanations.rad, rad_graph,
            explanations.pu, pu_graph,
            explanations.pg, pg_graph,
            explanations.anim], state


def create_antipodal_pairs_figure(points, convex_hull, antipodal_pairs):
    draw_points = np.vstack((points, points[0]))
    draw_ch = np.vstack((convex_hull, convex_hull[0]))

    fig = create_base_figure()

    # Plot base polygon
    fig.add_trace(go.Scatter(
        x=draw_points[:, 0],
        y=draw_points[:, 1],
        mode='lines',
        fill='toself',
        fillcolor='#2D4262'
    ))
    # Plot convex hull
    fig.add_trace(go.Scatter(
        x=draw_ch[:, 0],
        y=draw_ch[:, 1],
        mode='lines',
        line=go.scatter.Line(color='black', width=4)
    ))
    # Plot antipodal pairs
    for p1, p2 in antipodal_pairs:
        x1, y1 = convex_hull[p1]
        x2, y2 = convex_hull[p2]
        fig.add_trace(go.Scatter(
            x=[x1, x2],
            y=[y1, y2],
            mode='lines',
            line=go.scatter.Line(color='#DB9501')
        ))
    return fig


def create_function_figure(func_callable, minima, maxima, domain=(0, 2 * np.pi), latex=True):
    steps = round((domain[1] - domain[0]) / (np.pi / 2)) + 1
    ticktext = utils.generate_latex_text(domain[0], steps) if latex else utils.generate_degree_text(domain, steps)
    fig = go.Figure(
        layout=go.Layout(
            showlegend=False,
            xaxis=go.layout.XAxis(
                tickmode='array',
                tickvals=np.linspace(*domain, steps),
                ticktext=ticktext,
                range=domain,
                # fixedrange=True
            ))
    )

    x = np.linspace(*domain, 1000)
    y = np.array([func_callable(t) for t in x])

    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines',
        line=go.scatter.Line(color='black')
    ))

    y_lower = max(0, min(y) - 20)

    for e in minima:
        fig.add_trace(go.Scatter(
            x=[e, e],
            y=[y_lower, func_callable(e)],
            mode='lines',
            line=go.scatter.Line(color='blue')
        ))

    for e in maxima:
        fig.add_trace(go.Scatter(
            x=[e, e],
            y=[y_lower, func_callable(e)],
            mode='lines',
            line=go.scatter.Line(color='red')
        ))

    return fig


def create_transfer_figure(transfer_callable, domain=(0, 2 * np.pi), latex=True):
    x = np.linspace(*domain, 1000)
    y = np.array([transfer_callable(t) for t in x])

    steps = round((domain[1] - domain[0]) / (np.pi / 2)) + 1

    def padded_domain(a, b, pad=0.05):
        width = b - a
        padding = pad*width
        return a - padding, b + padding

    xdomain_padded = padded_domain(*domain, pad=0)
    ydomain_padded = padded_domain(min(domain[0], *y), max(domain[1], *y))

    ticktext = utils.generate_latex_text(domain[0], steps) if latex else utils.generate_degree_text(domain, steps)

    fig = create_base_figure()
    fig.update_layout(
        yaxis=go.layout.YAxis(
            scaleanchor='x',
            scaleratio=1,
            tickmode='array',
            tickvals=np.linspace(*domain, steps),
            ticktext=ticktext,
            range=ydomain_padded,
            zerolinecolor='#A9A9A9'
        ),
        xaxis=go.layout.XAxis(
            tickmode='array',
            tickvals=np.linspace(*domain, steps),
            ticktext=ticktext,
            range=xdomain_padded,
            zerolinecolor='#A9A9A9'
        ),
    )

    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines',
        line=go.scatter.Line(color='black')
    ))

    return fig


def add_intervals_to_figure(transfer_fig: Union[go.Figure, dict], intervals: List[engine.Interval],
                            offset: float = -0.5, increment: float = 0.1):
    """Adds intervals found by the backchaining algorithm to below the x axis and to the left of the y axis. """
    if type(transfer_fig) is dict:
        transfer_fig = go.Figure(transfer_fig)

    # offset = -0.1

    for i in intervals:
        transfer_fig.add_trace(
            go.Scatter(
                x=[i.a, i.b],
                y=[offset, offset],
                mode='lines+markers',
                line=go.scatter.Line(color='#2D4262')
            )
        )

        transfer_fig.add_trace(
            go.Scatter(
                x=[offset, offset],
                y=[i.image.a, i.image.b],
                mode='lines+markers',
                line=go.scatter.Line(color='#DB9501')
            )
        )

        offset -= increment

    # setting the axis range and ticklabel positions
    def domain_and_position(domain):
        domain = (min(offset, domain[0]), domain[1])
        pos = (0 - domain[0]) / (domain[1] - domain[0])

        return domain, pos

    xdomain, xpos = domain_and_position(transfer_fig.layout.xaxis.range)
    ydomain, ypos = domain_and_position(transfer_fig.layout.yaxis.range)

    transfer_fig.update_layout(xaxis_range=xdomain, yaxis_range=ydomain)

    return transfer_fig


def create_base_figure():
    fig = go.Figure(
        layout=go.Layout(
            yaxis=go.layout.YAxis(scaleanchor='x'),
            xaxis=go.layout.XAxis(),
            showlegend=False
        )
    )
    return fig


def create_graph_from_figure(figure, id):
    graph = dcc.Graph(
        id=id,
        figure=figure,
        style={'width': '50vw', 'height': '50vw', 'max-width': '800px', 'max-height': '800px', 'margin': 'auto'},
        config={'displayModeBar': False, 'staticPlot': True}
    )

    return graph
