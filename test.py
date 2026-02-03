from indeterminatebeam import Beam
# Create 7 m beam with E, I, A as defaults
beam = Beam(7)                          
# Create 9 m beam with E, I, and A assigned by user
beam_2 = Beam(9, E=2000, I=10**6, A=3000)     

from indeterminatebeam import Support
# Defines a pin support at location x = 5 m  
a = Support(5, (1,1,0))      
# Defines a roller support at location x = 0 m
b = Support(0, (0,1,0))      
# Defines a fixed support at location x = 7 m
c = Support(7, (1,1,1))      
# Assign the support objects to a beam object created earlier
beam.add_supports(a,b,c)    

from indeterminatebeam import PointLoadV, PointTorque, DistributedLoadV
# Create a 1000 N point load at x = 2 m
load_1 = PointLoadV(1000, 2)
# Create a 2000 N/m UDL from x = 1 m to x = 4 m
load_2 = DistributedLoadV(2000, (1, 4))
# Defines a 2 kN.m point torque at x = 3.5 m
load_3 = PointTorque(2*10**3, 3.5)
# Assign the load objects to the beam object
beam.add_loads(load_1,load_2,load_3)

beam.analyse()  
print(beam._bending_moments)

for i in range(0, 800):
    print(f"Bending moment at x={i} m: {beam.get_bending_moment(i)} N.m")