import dash_core_components as dcc

"""
This module contains all the explanations present on the 'generate plan' webpage. 
"""

ch_ap = dcc.Markdown('''
    ## The Polygon
    
    The polygon you entered is shaded in dark blue. The black outline represents the polygon's convex hull,
    which the algorithm uses to compute a plan. The gold lines that cross the polygon are antipodal
    pairs. Antipodal pairs are pairs of points that admit parallel supporting lines, which are used
    to compute the diameter function. For more on antipodal pairs, see Preparata and Shamos (1985).
    
    The convex hull is computed using Jarvis's March, which runs in O(nh) time. The antipodal pairs
    algorithm runs in O(n) time. 
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)

dia = dcc.Markdown('''
    ## The Diameter Function
    
    The diameter function represents the minimum distance between two parallel lines as they are rotated
    around the polygon. This is computed using an adapted version of the antipodal pairs algorithm. The
    diameter function is a piecewise function consisting of a series of sinusoids whose amplitude and 
    phase shift vary with respect to the polygon. For more info on computing the diameter function, see
    Goldberg (1993). 
    
    The red vertical lines represent the local maxima of the function, while the blue lines represent 
    the local minima. These extrema are used to compute the squeeze function, shown below.
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)

sq = dcc.Markdown('''
    ## The Squeeze Function
    
    The squeeze function is a transfer function that represents the output orientation of the part with
    respect to the gripper if the polygon was squeezed at a that angle with respect to the gripper. This is 
    computed by mapping ranges between local maxima to the local minimum in between. For more info on 
    the squeeze function, see Goldberg (1993). 
    
    The discontinuities in the squeeze function define s-intervals and s-images, which are used to
    compute the plan to orient the part. Below the x-axis in blue are the s-intervals found by the 
    backchaining algorithm, and to the left of the y-axis are the corresponding s-images. The s-interval
    on the top is the first interval found, corresponding to the largest single step in the squeeze function,
    while the interval on the bottom is the last interval found. Going from bottom to top, notice that 
    the s-intervals (and corresponding s-images) get smaller. This allows the backchaining algorithm to
    "funnel" the part into a unique final orientation. 
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)

rad = dcc.Markdown('''
    ## The Radius Function
    
    The radius function describes how the distance between a support line and the centroid of the 
    polygon varies as the support line is rotated around the part. As with before, the red lines 
    represent local maxima and blue lines represent local minima. Similar to the diameter function,
    the extrema of the radius function are used to compute another transfer function: the push function.
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)

pu = dcc.Markdown('''
    ## The Push Function
    
    The push function, similar to the squeeze function, is a transfer function that maps an initial
    orientation of a part of the final orientation after a part is pushed by a single gripper jaw for
    a sufficient distance such that one of the polygon's edges is aligned with the gripper.
    The push function is derived in the same fashion as the squeeze function is derived from the diameter
    function. For more information on the push and radius function, see Goldberg (1993).
    
    The push function is used to compute the push-grasp function, another transfer function that is used
    to compute a push-grasp plan.
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)

pg = dcc.Markdown('''
    ## The Push-Grasp Function
    
    The push-grasp function is computed by composing the push function with the squeeze function. This
    function (more specifically, its discontinuities) are used to generate a different plan that avoids
    several assumptions used in the squeeze function; in particular, the two jaws are no longer required 
    to contact the polygonal part at exactly the same time. At the same time, the plan orients the part
    to a _unique_ final orientation, instead of just up to symmetry. 
    
    As in the squeeze function plot, the s-intervals and corresponding s-images are below the x-axis 
    and to the right of the y-axis. 
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)

anim = dcc.Markdown(r'''
    ## The Animation
    
    Now let's take a look at the algorithm in action! The backchaining algorithm, using the intervals below the
    axis on the transfer function plots above, generates a series of squeezing actions that orient the part 
    *up to symmetry* for a squeeze plan and to a unique final orientation for a push-grasp plan.
    For most arbitrary polygons with no rotational symmetry, up to symmetry usually means that the part will be
    oriented at some angle theta or theta+pi/2.
    
    To view the animation, use the dropdown below to select the plan that you would like to see. The gripper angles
    that the algorithm generates are shown above the grippers in degrees. Please note that may take several seconds 
    for the animation to begin, so please wait after you select an animation.
    ''',
    style={'width': '70vw', 'margin': 'auto', 'text-align': 'center'}
)