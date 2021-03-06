# Orienting Polygonal Parts without Sensors: An Implementation in Python

This is a web browser implmentation of [Prof. Ken Goldberg's](https://goldberg.berkeley.edu/) PhD 
Thesis [Orienting Polygonal Parts Without Sensors (1993)](https://goldberg.berkeley.edu/pubs/algo93.pdf),
which describes an algorithm for computing a series of squeeze actions that orient polygonal parts
*up to symmetry*. A Java implementation of the algorithm can be found [here](https://goldberg.berkeley.edu/part-feeder/),
and for more background on the algorithm can be found [here](https://goldberg.berkeley.edu/feeder/)
or by reading the thesis. A deployment of this web application can be viewed here: 
[https://rieff.bair.berkeley.edu/part-feeder/](https://rieff.bair.berkeley.edu/part-feeder/).

This is written in Python using the [Flask](https://flask.palletsprojects.com/) 
web framework, [Dash](https://dash.plotly.com/) and [Plotly](https://plotly.com/python/) 
for interactive web plotting, and [pymunk](http://www.pymunk.org/en/latest/) to simulate the squeeze
actions for the animation.

Update V1.7: This now uses [planck.js](https://piqnt.com/planck.js/) for clientside simulation of the 
squeeze and push-grasp plans for the animation to avoid putting heavy load on the server.

## Description of files
The application is contained within the [part-feeder folder](part_feeder/). Inside that folder:
* [engine.py](part_feeder/engine.py) contains the functions related to the algorithm itself
* [feeder.py](part_feeder/feeder.py) uses the functions in engine.py to execute the algorithm and
generate the plots
* [anim.py](part_feeder/anim.py) contains the simulation of the squeeze actions using pymunk
* [explanations.py](part_feeder/explanations.py) contains the text seen on the webpage
* [gallery.py](part_feeder/gallery.py) contains the Gallery page generation
* [anim.js](part_feeder/static/js/anim.js) contains a full port of `anim.py` to Javascript using the `planck.js` 2D physics engine
