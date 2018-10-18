from __future__ import print_function
get_ipython().magic(u'matplotlib nbagg')
from openbte.geometry import *
from openbte.solver import *
from openbte.material import *
from openbte.plot import *
from ipywidgets import interact, interactive, fixed, interact_manual,HBox,VBox
import ipywidgets as widgets
from IPython.display import display
from ipywidgets import Button, GridBox, Layout, ButtonStyle

#

t = widgets.Text(value = 'Thermal Conductivity [W/m/K]: ')

sel = widgets.Select(
    options=['Geometry',' '],
    value='Geometry',
    description='Variable',
    disabled=False
)

w = widgets.FloatSlider(
    value=0.2,
    min=0.01,
    max=0.3,
    step=0.01,
    description='Porosity:',
    disabled=False,
    continuous_update=False,
    orientation='horizontal',
    readout=True,
    readout_format='.3f')
w.style.handle_color = 'lightblue'


def create_geometry(porosity,shape,angle,lattice):

    if lattice == 'squared':
     type = 'porous/square_lattice'
     step = 0.1
    if lattice == 'staggered':
     type = 'porous/staggered_lattice'
     step = 0.2
    if lattice == 'honeycomb':
      type = 'porous/hexagonal_lattice'
      step = 0.1 *np.sqrt(sqrt(3.0))

    geo = Geometry(type = type,shape=shape,
                                  lx = 1.0, ly = 1.0,\
                                  step=step/1.0,\
                                  angle=angle,\
                                  porosity=porosity,
                                  inclusion = True,
                                  mesh=True,plot=False);


    sel.options=['Geometry',' ']
    sel.value = ' '
    sel.value = 'Geometry'
    t.value = 'Thermal Conductivity [W/m/K]: '


def create_material(kappa_matrix,kappa_inclusion):
    Material(region='Matrix',kappa = kappa_matrix,filename='material_a');
    Material(region='Inclusion',kappa = kappa_inclusion,filename='material_b');
    w.value = w.value


def plot_data(variable):

 if not variable in ['Geometry',' '] :
  if variable == 'Flux (Magnitude)':
      var = 'fourier_flux'
      direction = 'magnitude'
  elif variable == 'Flux (X)':
      var = 'fourier_flux'
      direction = 'x'
  elif variable == 'Flux (Y)':
      var = 'fourier_flux'
      direction = 'y'
  elif variable == 'Temperature':
      var = 'fourier_temperature'
      direction = None

  Plot(variable='map/' + var,direction=direction,show=True,write=False,streamlines=False,repeat_x=1,repeat_y =1,plot_interfaces=True)
  Plot(variable='line/'+ var,direction=direction,show=True,write=False,streamlines=False,repeat_x=1,repeat_y =1,plot_interfaces=True)


 if variable == 'Geometry':
  Geometry(type='load',filename = 'geometry',plot=True)

def run(b):
 sol = Solver(max_bte_iter = 0,verbose=False);


 kappa = sol.state['kappa_fourier']
 #if b.value==0:
 # display(t)
 t.value = 'Thermal Conductivity [W/m/K]: '.ljust(20) +  '{:8.2f}'.format(kappa)
 b.value +=1
 sel.options=['Geometry','Flux (X)', 'Flux (Y)', 'Flux (Magnitude)','Temperature']

 sel.value = 'Flux (Magnitude)'



w = widgets.FloatSlider(
    value=0.2,
    min=0.01,
    max=0.3,
    step=0.01,
    description='Porosity:',
    disabled=False,
    continuous_update=False,
    orientation='horizontal',
    readout=True,
    readout_format='.3f')
w.style.handle_color = 'lightblue'


d = widgets.RadioButtons(
    options=['circle', 'square', 'triangle'],
    value='circle',
    description='shape:',
    disabled=False
)

l = widgets.RadioButtons(
    options=['squared', 'staggered', 'honeycomb'],
    value='squared',
    description='Pore lattice:',
    disabled=False
)

a = widgets.FloatSlider(
    value=0.0,
    min=0.0,
    max=360,
    step=10,
    description='Angle:',
    disabled=False,
    continuous_update=False,
    orientation='horizontal',
    readout=True,
    readout_format='.0f')
a.style.handle_color = 'lightblue'


km = widgets.BoundedFloatText(
    value=150.0,
    min=1,
    max=1000,
    step=0.1,
    description='Matrix [W/K/m]',
    disabled=False,
    layout = {'width': '300px'},\
    style = {'description_width': '150px'})

ki = widgets.BoundedFloatText(
    value=0.0,
    min=0,
    max=1000,
    step=0.1,
    description='Inclusion [W/K/m]',
    disabled=False,
    layout = {'width': '300px'},\
    style = {'description_width': '150px'})



#plot geometry-------
test = interactive(create_geometry, porosity=w, shape=d, angle=a,lattice=l);
v3 = interactive(create_material, kappa_matrix=km,kappa_inclusion=ki);

v1 = VBox(test.children[0:2])
v2 = VBox(test.children[2:4])
display(HBox([v1,v2,v3]))
#--------------------


v = interactive(plot_data,variable=sel);

display(v)


#plot output-------
button = widgets.Button(description="Run");
button.value = 0
button.on_click(run)
display(HBox([button,t]))
#-------------------





#
