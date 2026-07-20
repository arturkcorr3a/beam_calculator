from src.beam.rectangular_beam import RectangularBeam
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from indeterminatebeam import Support, DistributedLoadV

from src.reinforcement.rebar_calculator import RebarCalculator
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups

# Geometria
length =  500  # cm
width  =   20  # cm
height =   50  # cm

# Bi-apoiada:
a = Support(0,(1,1,0))       # Defines a pin support at location x = 0 m  
b = Support(length,(1,1,0))  # Defines a pin support at location x = 5 m  

concrete = Concrete.C30
steel = Steel.CA50

area = width/100 * height/100  # m²
peso = 25 * area  # kN/m
peso_proprio = DistributedLoadV(-peso, (0, length))  # kN/m, distributed load along the entire beam length

supports = [a, b]  # List of supports (indeterminatebeam.Support instances)
loads = [peso_proprio]  # List of loads (indeterminatebeam.Load instances)

beam = RectangularBeam(length, width, height, concrete, steel, supports, loads)

max_bending_moment = beam.get_bending_moment(return_max=True)  # kN.m
design_shear_force = beam.get_shear_force(return_max=True) * 1.4 # kN

stirrup_calculator = StirrupCalculator(beam, design_shear_force)
stirrups = Stirrups(beam, stirrup_calculator)
calculator = RebarCalculator(beam, max_bending_moment, stirrups)
calculator.calculate()

compressed = calculator.compressed_reinforcement
tensioned = calculator.tensioned_reinforcement

tensioned.print_report()
stirrups.print_report()

if compressed.is_chosen:
    print(f"Compressed rebar area: {compressed.required_area} cm²")
# beam.print_results_table()

# fig1 = beam.plot_beam_external()
# fig1.show()
# 
# fig2 = beam.plot_beam_internal()
# fig2.show()