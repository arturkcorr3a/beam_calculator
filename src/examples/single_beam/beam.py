# type: ignore

# cSpell:disable

from indeterminatebeam import UDLV, Support

from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.loading.forces import design_effort_elu
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam

# ==============================================================================
# 1. INPUT DATA / DADOS DE ENTRADA
# ==============================================================================
span1 = 621.5  # cm
span2 = 620  # cm
span3 = 781.5  # cm
length = span1 + span2 + span3  # cm

width = 19  # cm
height = 65  # cm

concrete = Concrete.C40
steel = Steel.CA50

# Contínua (sem considerações de rigidez)
fixed = (1, 1, 0)
p1 = Support(0, fixed)
p2 = Support(span1, fixed)
p3 = Support(span1 + span2, fixed)
p4 = Support(length, fixed)

# Carregamento (sinal negativo pq é para baixo)
load1 = -15.710  # kN/m -20.3 #
load2 = -14.479  # kN/m -20.3 #
load3 = -31.672  # kN/m -20.3 #

load_span1 = UDLV(load1, (0, span1))
load_span2 = UDLV(load2, (span1, span1 + span2))
load_span3 = UDLV(load3, (span1 + span2, length))

supports = [p1, p2, p3, p4]
loads = [load_span1, load_span2, load_span3]

beam = RectangularBeam(length, width, height, concrete, steel, supports, loads)

# ==============================================================================
# 2. STRUCTURAL ANALYSIS / ESFORÇOS SOLICITANTES
# ==============================================================================
max_bending_moment, position = beam.get_max_bending_moment()  # kN.m
max_shear_force = beam.get_shear_force(return_max=True)  # kN

design_bending_moment = design_effort_elu(max_bending_moment)  # kN.m
design_shear_force = design_effort_elu(max_shear_force)  # kN

# ==============================================================================
# 3. CALCULATIONS / PROCESSAMENTO DO DIMENSIONAMENTO
# ==============================================================================
stirrup_calculator = StirrupCalculator(beam, design_shear_force)
stirrups = Stirrups(beam, stirrup_calculator)

calculator = RebarCalculator(beam, max_bending_moment, stirrups, position)
calculator.calculate()

compressed = calculator.compressed_reinforcement
tensioned = calculator.tensioned_reinforcement
